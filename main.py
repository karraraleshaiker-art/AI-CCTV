import getpass, json, os, threading, time
from pathlib import Path
from urllib.parse import quote
import cv2, numpy as np, psutil
from ultralytics import YOLO

ROOT=Path(__file__).resolve().parent
S=json.loads((ROOT/"settings.json").read_text(encoding="utf-8"))
PERSON_CLASS=0; PHONE_CLASS=67
GREEN=(0,220,0); RED=(0,0,255); WHITE=(255,255,255)

def rtsp_url(user,pwd,cam,suffix):
    return f"rtsp://{quote(user,safe='')}:{quote(pwd,safe='')}@{S['nvr_ip']}:{S['rtsp_port']}/Streaming/channels/{cam}{suffix}"

class LatestFrameCapture:
    def __init__(self,user,pwd,cam,suffix):
        self.user=user; self.pwd=pwd; self.cam=cam; self.suffix=suffix
        self.lock=threading.Lock(); self.frame=None; self.seq=0
        self.running=False; self.thread=None; self.cap=None; self.status="STOPPED"
    def _open(self):
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS","rtsp_transport;tcp")
        cap=cv2.VideoCapture(rtsp_url(self.user,self.pwd,self.cam,self.suffix),cv2.CAP_FFMPEG)
        try: cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        except: pass
        return cap
    def start(self):
        self.running=True
        self.thread=threading.Thread(target=self._loop,daemon=True); self.thread.start()
    def _loop(self):
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self.status="CONNECTING"; self.cap=self._open()
                if not self.cap.isOpened():
                    self.status="RETRYING"; time.sleep(1); continue
                self.status="LIVE"
            ok,f=self.cap.read()
            if not ok or f is None:
                self.status="RECONNECTING"
                self.cap.release(); self.cap=None; time.sleep(.2); continue
            with self.lock:
                self.frame=f; self.seq+=1
    def get(self):
        with self.lock:
            return (None,self.seq) if self.frame is None else (self.frame.copy(),self.seq)
    def stop(self):
        self.running=False
        if self.cap is not None: self.cap.release()
        if self.thread is not None: self.thread.join(timeout=2)

class AIWorker:
    def __init__(self,capture):
        self.capture=capture; self.lock=threading.Lock()
        self.dets=[]; self.error=""; self.running=False
        self.thread=None; self.model=None; self.ai_fps=0.0; self.ms=0.0
    def start(self):
        self.running=True
        self.thread=threading.Thread(target=self._loop,daemon=True); self.thread.start()
    def _loop(self):
        print(f"[MODEL] Loading {S['model']} ...")
        self.model=YOLO(S["model"]); print("[MODEL] Ready.")
        last_seq=-1; last_run=0.0; n=0; t=time.time()
        min_dt=1/max(1.0,float(S["max_ai_fps"]))
        while self.running:
            if time.time()-last_run<min_dt: time.sleep(.002); continue
            frame,seq=self.capture.get()
            if frame is None or seq==last_seq: time.sleep(.004); continue
            last_seq=seq; last_run=time.time(); t0=time.perf_counter()
            try:
                r=self.model.track(frame,persist=True,tracker=S["tracker"],imgsz=S["imgsz"],
                    conf=min(S["person_conf"],S["phone_conf"]),iou=S["iou"],
                    classes=[PERSON_CLASS,PHONE_CLASS],verbose=False,device="cpu")[0]
                dets=[]
                if r.boxes is not None and len(r.boxes):
                    boxes=r.boxes.xyxy.cpu().numpy(); cls=r.boxes.cls.cpu().numpy().astype(int)
                    conf=r.boxes.conf.cpu().numpy()
                    ids=r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else np.full(len(boxes),-1)
                    for b,c,cf,tid in zip(boxes,cls,conf,ids):
                        if c==PERSON_CLASS and cf>=S["person_conf"]:
                            dets.append(("person",b.tolist(),float(cf),int(tid)))
                        elif c==PHONE_CLASS and cf>=S["phone_conf"]:
                            dets.append(("phone",b.tolist(),float(cf),int(tid)))
                with self.lock: self.dets=dets; self.error=""
            except Exception as e:
                with self.lock: self.error=str(e)
            self.ms=(time.perf_counter()-t0)*1000
            n+=1; dt=time.time()-t
            if dt>=1: self.ai_fps=n/dt; n=0; t=time.time()
    def snapshot(self):
        with self.lock: return list(self.dets),self.error
    def reset_tracker(self):
        with self.lock: self.dets=[]
        self.model=YOLO(S["model"])
    def stop(self):
        self.running=False
        if self.thread is not None: self.thread.join(timeout=3)

def draw(frame,dets,cam,stream,ai_fps,ms):
    out=frame.copy(); people=0; phones=0
    for typ,b,cf,tid in dets:
        x1,y1,x2,y2=map(int,b)
        if typ=="person":
            people+=1; color=GREEN; label=f"Person {tid if tid>=0 else '?'} | {cf:.2f}"
        else:
            phones+=1; color=RED; label=f"PHONE | {cf:.2f}"
        cv2.rectangle(out,(x1,y1),(x2,y2),color,2)
        cv2.putText(out,label,(x1,max(22,y1-7)),cv2.FONT_HERSHEY_SIMPLEX,.58,color,2)
    cv2.rectangle(out,(0,0),(650,74),(0,0,0),-1)
    cv2.putText(out,f"{cam} | {stream} | People {people} | Phones {phones}",(12,28),
                cv2.FONT_HERSHEY_SIMPLEX,.68,WHITE,2)
    cv2.putText(out,f"AI {ai_fps:.1f} FPS | {ms:.0f} ms",(12,58),
                cv2.FONT_HERSHEY_SIMPLEX,.62,WHITE,2)
    if out.shape[1]>S["display_max_width"]:
        sc=S["display_max_width"]/out.shape[1]
        out=cv2.resize(out,(int(out.shape[1]*sc),int(out.shape[0]*sc)),interpolation=cv2.INTER_AREA)
    return out

def startup():
    print("\n=== AI CCTV v0.4 - Stable Core ===")
    print("Person + phone only. No pose, face ID, or recording.\n")
    user=input("NVR username: ").strip()
    pwd=getpass.getpass("NVR password: ")
    while True:
        raw=input("Starting camera channel (example 14): ").strip().upper()
        raw=raw[1:] if raw.startswith("D") else raw
        if raw.isdigit() and int(raw)>0: cam=int(raw); break
        print("Invalid camera.")
    st=input("Stream: 1=Main, 2=Sub [1]: ").strip() or "1"
    suffix="01" if st!="2" else "02"
    return user,pwd,cam,suffix,("MAIN" if suffix=="01" else "SUB")

def main():
    user,pwd,cam,suffix,stream=startup()
    capture=LatestFrameCapture(user,pwd,cam,suffix); capture.start()
    print("[RTSP] Waiting for first frame...")
    deadline=time.time()+15
    while time.time()<deadline:
        f,_=capture.get()
        if f is not None: break
        time.sleep(.1)
    else:
        capture.stop(); print("ERROR: No camera frame."); input("Press Enter..."); return 1

    ai=AIWorker(capture); ai.start()
    label=f"D{cam}"; last_perf=0

    def switch(newcam):
        nonlocal capture,cam,label
        if newcam<1:return
        print(f"[CAMERA] Switching D{cam} -> D{newcam} ...")
        capture.stop()
        newcap=LatestFrameCapture(user,pwd,newcam,suffix); newcap.start()
        deadline=time.time()+12
        while time.time()<deadline:
            f,_=newcap.get()
            if f is not None:
                capture=newcap; cam=newcam; label=f"D{cam}"
                ai.capture=capture; ai.reset_tracker()
                print(f"[CAMERA] Monitoring {label}")
                return
            time.sleep(.1)
        print(f"[CAMERA] D{newcam} unavailable. Returning to D{cam}.")
        newcap.stop()
        capture=LatestFrameCapture(user,pwd,cam,suffix); capture.start()
        ai.capture=capture; ai.reset_tracker()

    print("\nControls: Q/ESC quit | N next | P previous | C choose camera\n")
    try:
        while True:
            frame,_=capture.get()
            if frame is None: time.sleep(.01); continue
            dets,error=ai.snapshot()
            shown=draw(frame,dets,label,stream,ai.ai_fps,ai.ms)
            if error:
                cv2.putText(shown,"AI ERROR: "+error[:80],(12,shown.shape[0]-18),
                            cv2.FONT_HERSHEY_SIMPLEX,.5,RED,2)
            cv2.imshow("AI CCTV v0.4 - Stable Core",shown)

            if time.time()-last_perf>=2:
                last_perf=time.time(); vm=psutil.virtual_memory()
                print(f"[PERF] {label} | CPU {psutil.cpu_percent():.1f}% | RAM {vm.percent:.1f}% | AI {ai.ai_fps:.1f} FPS | {ai.ms:.0f} ms | RTSP {capture.status}",flush=True)

            k=cv2.waitKey(1)&0xFF
            if k in (ord("q"),ord("Q"),27): break
            elif k in (ord("n"),ord("N")): switch(cam+1)
            elif k in (ord("p"),ord("P")): switch(max(1,cam-1))
            elif k in (ord("c"),ord("C")):
                raw=input("\nCamera channel: ").strip().upper()
                raw=raw[1:] if raw.startswith("D") else raw
                if raw.isdigit(): switch(int(raw))
    finally:
        ai.stop(); capture.stop(); cv2.destroyAllWindows()
    print("Stable Core stopped cleanly.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
