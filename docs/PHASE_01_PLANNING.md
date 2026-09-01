# Phase 1: Planning And Discovery

## Purpose

Phase 1 is not about writing code first. It is about understanding the factory rules clearly enough that the software will match real operations.

This matters because the project is becoming bigger than AI CCTV. It is now a factory automation project. If we build without planning, we may create screens and features that do not match how managers and employees actually work.

## Main Goal

Create a clear project blueprint for the first version of the factory workforce system.

The first version should prepare the factory for future AI CCTV integration, but it should solve daily HR and shift management problems first.

## Why This Phase Comes Before AI CCTV

The AI CCTV system needs context.

For example:

- Who is working today?
- Is the person assigned to morning shift or night shift?
- Which employee is assigned to this zone?
- Did this employee officially swap shifts with another employee?
- Is this person on approved leave?
- Did the manager approve a temporary change?

Without this information, the AI CCTV system may create false alerts. The camera can see movement, but it cannot understand approved factory decisions unless those decisions are stored in a system.

## Phase 1 Deliverables

By the end of Phase 1, we should have:

- confirmed project scope
- list of user roles
- employee data fields
- shift rules
- leave and holiday rules
- rest hour rules
- shift swap workflow
- manager approval workflow
- first version feature list
- future feature list
- security and privacy notes
- development roadmap

## Users To Understand

### Employee

Needs:

- view current shift
- request rest hour
- request leave or holiday
- request shift swap
- accept or reject swap from another employee
- see approval status

### Manager Or Supervisor

Needs:

- see pending requests
- approve or reject requests
- see who is working today
- see who is absent
- check shift coverage
- review employee history

### HR Or Admin

Needs:

- add and edit employees
- manage leave balance
- manage departments and roles
- correct records
- export reports
- control permissions

### System Owner

Needs:

- backups
- audit logs
- security controls
- future integration with attendance and AI CCTV

## Important Questions For Management

### Employee Data

- What employee information is currently stored?
- Is it on paper, Excel, or another system?
- What is the employee ID format?
- Are employees grouped by department, production line, or work zone?
- Who is allowed to add or edit employee data?

### Shift Rules

- Are there only two shifts: morning and night?
- What are the exact start and end times?
- Can employees change shifts temporarily?
- Can employees swap shifts directly with each other?
- Does every shift swap require manager approval?
- Are some roles not allowed to swap?

### Leave And Holiday Rules

- How many leave days does each employee get?
- Are leave balances yearly, monthly, or custom?
- Can two employees from the same department take leave on the same day?
- Who approves leave?
- Can managers override the system?
- Are there emergency leave rules?

### Rest Hour Rules

- How many rest hours are allowed?
- Is rest hour paid or unpaid?
- Does it require manager approval?
- Can more than one employee from the same area rest at the same time?

### Approval Rules

- Who approves requests?
- Is there one approval level or multiple levels?
- What happens if a manager does not respond?
- Should rejected requests require a reason?
- Should employees receive notifications?

### Reports

- What reports do managers need every day?
- What reports does HR need every month?
- Do reports need to be exported to Excel or PDF?

### Future AI CCTV

- Which factory zones may later be monitored?
- Should AI alerts be linked to a shift schedule?
- Who is allowed to review AI alerts?
- What should happen when the AI creates an alert?

## First Version Scope Proposal

The first version should include:

- employee database
- role-based login
- manager dashboard
- leave request
- rest hour request
- shift swap request
- manager approval/rejection
- request history
- basic shift calendar
- basic reports

The first version should not include:

- face recognition
- fingerprint/biometric system
- full AI CCTV integration
- payroll automation
- complex attendance hardware

These can come later after the foundation is accepted and stable.

## Phase 1 Success Criteria

Phase 1 is complete when:

- management agrees on the first version scope
- employee and shift rules are documented
- approval workflows are clear
- privacy concerns are understood
- the development roadmap is approved
- we know exactly what to build in Phase 2

