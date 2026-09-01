# Factory Automation Project Roadmap

## Project Direction

The project is moving from a standalone AI CCTV idea into a full factory automation system. The AI CCTV module should remain part of the long-term vision, but it should not be the first operational system we build.

The correct first step is to create the factory management foundation: employees, shifts, requests, approvals, leave balances, attendance records, and manager visibility. Once that data exists, future AI camera alerts can be connected to real approved schedules and zone assignments.

## Guiding Principle

Build the system step by step:

1. Make daily factory operations easier.
2. Organize employee and shift data.
3. Digitize approvals and requests.
4. Add reporting and attendance.
5. Integrate AI CCTV only after the operational foundation is ready.

## Suggested Phases

### Phase 1: Planning And Discovery

Goal: understand factory rules, employee structure, shift rules, approval workflows, and manager expectations before building.

Main output:

- project scope
- employee data requirements
- shift and leave rules
- approval workflow map
- user roles
- first version feature list
- risks and decisions

### Phase 2: Core Workforce Database

Goal: replace scattered paper/Excel records with a clean digital employee database.

Main features:

- employee profiles
- departments or production areas
- job roles
- manager/supervisor assignment
- morning/night shift assignment
- leave balance fields
- employee status: active, inactive, suspended, resigned

### Phase 3: Request And Approval System

Goal: allow employees to request actions digitally and allow managers to approve or reject them.

Main features:

- leave request
- holiday scheduling
- rest hour request
- shift swap request
- two-employee agreement for shift swaps
- manager approval
- request history
- comments and rejection reasons

### Phase 4: Scheduling And Attendance Foundation

Goal: make the system understand who should be working, when, and where.

Main features:

- shift calendar
- daily staffing view
- planned absences
- attendance record
- manual attendance correction by authorized manager
- optional QR/PIN/badge attendance later

### Phase 5: Manager Dashboard And Reports

Goal: give managers useful visibility without depending on paper.

Main features:

- pending approvals
- employees on leave today
- shift coverage
- department staffing
- request statistics
- exportable reports
- audit history

### Phase 6: Employee Mobile Portal

Goal: let employees use the system from their phones with a simple interface.

Main features:

- login
- view shift
- request leave or rest hour
- request shift swap
- accept or reject swap request
- view request status
- view leave balance

### Phase 7: AI CCTV Integration

Goal: connect AI CCTV monitoring to the real factory workforce data.

The AI module can then use:

- approved shift schedules
- zone assignments
- active employee list
- approved shift swaps
- leave records
- attendance status

This reduces false alerts because the AI will not guess who should be in a place. It will compare camera events with approved operational data.

### Phase 8: Hardening, Security, And Scale

Goal: prepare the system for reliable daily use.

Main work:

- role-based permissions
- backups
- audit logs
- data privacy rules
- admin controls
- performance improvements
- deployment plan
- disaster recovery

## Recommended First Build

The first real software version should not try to include everything. It should focus on:

- employee database
- manager dashboard
- leave request
- rest hour request
- shift swap request
- approval flow
- basic reports

This gives the factory immediate value and creates the foundation for attendance and AI later.

