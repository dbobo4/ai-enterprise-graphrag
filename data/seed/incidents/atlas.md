# Incident report — September 2026 API outage

On 2026-09-18, Project Atlas suffered an API outage lasting 42 minutes. The root cause was an incorrect gateway routing rule introduced during deployment. The incident is closed. Requests accepted before the change remained queued, while new requests to the affected route failed until the previous rule was restored.

The duty engineer opened the incident after the first two telephone reports described the same failure. A direct check confirmed that the entry point was reachable but the route to the ticket service was wrong. The team paused the deployment, retained the proposed configuration and compared it with the last accepted version. The shared mailbox continued accepting support requests during the interruption.

Recovery replaced the faulty rule and replayed the affected requests in submission order. The support coordinator checked for duplicates before clearing the incident queue. No attachment was deliberately removed during the replay. The first successful response was followed by a short observation period, and the duty engineer confirmed that a newly submitted request reached the expected team.

The configuration review found that the deployment checklist did not require an automated route comparison. The corrective action adds validation for the entry path and its destination before a rule is accepted. Emergency changes must retain the same review evidence even when the normal deployment window cannot be used. The revised checklist was accepted at the October service review.

The incident owner separated customer-facing interruption time from the later reconciliation work. The latter continued after access had been restored and is not included in the 42-minute outage. The team will rehearse the rollback with a deliberately invalid route before the next major release. The support coordinator will retain the replay log with the approved closure record.
