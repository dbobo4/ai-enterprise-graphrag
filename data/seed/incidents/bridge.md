# Incident report — October 2026 onboarding delays

On 2026-10-09, Project Bridge experienced onboarding delays affecting 18 applications. The root cause was repeated timeouts in the external identity verification service. The incident is closed. Submitted starter details remained available, but the affected applications did not receive a final verification status during the first appointment window.

The HR coordinator noticed that several applicants had completed the document step without moving to approval. Support compared request identifiers before submitting any check again. The application entry form was still responding, and completed checks from the earlier morning remained visible. The team paused repeated manual submissions to avoid duplicate verification attempts and additional charges.

Recovery introduced retries with bounded timeouts and a supervised manual appointment process. The manual reviewer recorded the reason for using the alternative route. Each affected application retained its original employee number and appointment history. HR contacted applicants whose appointments had moved, rather than asking them to create another application from the beginning.

The incident review distinguished an unreadable image from an interrupted service request. An unreadable image needs correction by the applicant, while an interrupted request first needs a status check. The helpdesk guide now asks the coordinator to record the request identifier before escalation. Support also checks whether an interrupted attempt completed after the local timeout expired.

The closure meeting confirmed that all 18 applications had either progressed or received a named manual appointment. This figure counts affected applications rather than distinct service attempts. Finance will review interrupted-attempt invoice lines separately. HR will inspect the next month's exception queue to confirm that staff are using the bounded retry process and recording the required reviewer.
