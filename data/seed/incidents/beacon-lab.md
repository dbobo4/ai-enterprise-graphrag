# Incident report — October 2026 sandbox alert loop

On 2026-10-16, Project Beacon Lab generated repeated sandbox alerts. The root cause was a duplicate alert subscription left enabled after a training exercise. The incident is closed. The repeated notifications reached the finance training queue; they did not release payment instructions or change the production duty engineer's contact schedule.

The trainer reported that a restored sample session produced two notifications for one mismatch. Finance compared the sample event identifiers and confirmed that the reconciliation exercise itself had run once. A review of the subscription list found an old practice subscription alongside the active one. Support preserved the subscription settings before disabling the duplicate entry.

Recovery removed the duplicate subscription and repeated the sample exercise under supervision. The trainer checked both notification delivery and removal of the temporary output files. The exercise log retained the original mismatch reference so that attendance records did not show a second completed exercise. The finance coordinator confirmed that the sandbox queue had returned to its normal volume.

The corrective action adds a subscription review to the end-of-session checklist. A restored practice account must not inherit an obsolete training contact list. The analyst responsible for a session confirms the expiry time of any temporary alert suppression. A known exercise warning can be grouped for the session, but its original event identifier must remain available.

The next monthly review will compare unattended alerts with booked training periods. Finance has asked for the monitoring summary to keep sandbox and production figures separate. The incident does not expand the approved network scope. Any proposal to connect a real payment service still requires a new review and written approval outside the sandbox training process.
