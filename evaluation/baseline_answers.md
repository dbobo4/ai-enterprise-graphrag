# Benchmark answers

HelioWorks has 34 synthetic business documents and 170 chunks, split at 650 characters with 65-character overlap. Vector Standard retrieves 4 excerpts per question (2.35% of the chunks). All modes use the same 12 seed-only questions.

- Vector Standard: one vector search, top_k=4.
- Vector Multi-step: up to three dependent vector searches, with verified extraction and one retry when needed.
- Graph RAG: validated read templates over reviewed facts, with selected supporting chunks; meeting and email-only facts can be unsupported.

Source coverage measures retrieved expected documents, not answer correctness. Times describe these runs, not a performance guarantee. Model calls include planning, extraction retries and answer generation. Counts cover finished questions, exclude readiness checks and are unavailable for errors. Embedding calls, token usage and monetary cost are not estimated.

## Results

| Mode | Category | Finished | Source coverage | Average time |
|---|---|---:|---:|---:|
| Vector Standard | Overall | 12/12 | 62.5% | 2.53 s |
| Vector Standard | local | 4/4 | 75.0% | 2.54 s |
| Vector Standard | multi-hop | 4/4 | 75.0% | 2.07 s |
| Vector Standard | global | 4/4 | 37.5% | 2.97 s |
| Vector Multi-step | Overall | 12/12 | 76.4% | 7.25 s |
| Vector Multi-step | local | 4/4 | 100.0% | 7.59 s |
| Vector Multi-step | multi-hop | 4/4 | 91.7% | 8.99 s |
| Vector Multi-step | global | 4/4 | 37.5% | 5.17 s |
| Graph RAG | Overall | 12/12 | 91.7% | 5.53 s |
| Graph RAG | local | 4/4 | 75.0% | 4.80 s |
| Graph RAG | multi-hop | 4/4 | 100.0% | 4.62 s |
| Graph RAG | global | 4/4 | 100.0% | 7.17 s |

Averages include finished questions, including incomplete retrieval; errors are listed below.

Vector Standard — completed 2026-11-18T01:08:35.955600+00:00; 12 model calls, 12 vector searches.

Vector Multi-step — completed 2026-11-18T01:09:57.582588+00:00; 45 model calls, 20 vector searches.

Graph RAG — completed 2026-11-18T01:11:38.611482+00:00; 23 model calls, 22 graph queries.

## Answers

### Q01 · local — Ki vezeti a Project Atlas Archive programot, és melyik napra tervezik az indulását?

Expected answer:

> Nóra Váradi; 2027-02-12.

Relevant sources: projects/atlas-archive.md.

**Vector Standard**

> A Project Atlas Archive programot Nóra Váradi vezeti, a tervezett indulás napja 2027. február 12. [Source: projects/atlas-archive.md#0]

Retrieved sources: projects/atlas-archive.md#0, projects/atlas.md#0, vendors/dataloom.md#0, meetings/atlas-operations.md#0.

Source coverage: 100.0% · Time: 2.09 s · Evidence: Expected sources found · 1 model calls, 1 vector searches.

**Vector Multi-step**

> A Project Atlas Archive programot Nóra Váradi vezeti, és a tervezett indulása 2027. február 12. [Source: projects/atlas-archive.md#0]

Retrieved sources: projects/atlas-archive.md#0, projects/atlas.md#0, vendors/dataloom.md#0, vendors/safedesk.md#0, people/roles.md#3, people/roles.md#0.

Source coverage: 100.0% · Time: 8.61 s · Evidence: Expected sources found · 5 model calls, 2 vector searches.

**Graph RAG**

> A Project Atlas Archive programot Nóra Váradi vezeti, és az indulását 2027. február 12-re tervezik. [Source: projects/atlas-archive.md#0]

Retrieved sources: projects/atlas-archive.md#0.

Source coverage: 100.0% · Time: 7.10 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q02 · local — Hány napra engedélyezhető először egy ideiglenes külsős fiók, és mennyivel a lejárat előtt kell kérni a megújítását?

Expected answer:

> Legfeljebb 30 napra; a megújítási kérelmet 5 nappal a lejárat előtt kell benyújtani.

Relevant sources: policies/access.md.

**Vector Standard**

> A rendelkezésre álló források nem tartalmaznak információt az ideiglenes külsős fiók első engedélyezési időtartamáról vagy a megújítás kérésének határidejéről.

Retrieved sources: vendors/novacloud.md#2, projects/beacon.md#0, projects/atlas.md#3, projects/atlas.md#4.

Source coverage: 0.0% · Time: 2.61 s · Evidence: Some expected sources missing · 1 model calls, 1 vector searches.

Note: Some expected source documents were not retrieved.

**Vector Multi-step**

> Nincs elegendő információ a korpuszban.

Retrieved sources: vendors/clearid.md#0, policies/access.md#0, projects/beacon-lab.md#0, projects/bridge.md#0, projects/beacon.md#0, vendors/greenwire.md#3, projects/beacon.md#5, vendors/novacloud.md#2.

Source coverage: 100.0% · Time: 7.15 s · Evidence: Intermediate evidence unverified · 4 model calls, 2 vector searches.

Note: A search step returned no evidence or its extracted answer could not be verified after one retry.

**Graph RAG**

> Egy ideiglenes külsős fiók kezdetben legfeljebb 30 napra engedélyezhető. A megújítást a lejárat előtt 5 nappal kell kérni. [Source: policies/access.md#0]

Retrieved sources: policies/access.md#0.

Source coverage: 100.0% · Time: 4.21 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q03 · local — Mi okozta a Project Bridge 2026. október 9-i onboarding elakadását, és hány jelentkezést érintett?

Expected answer:

> A külső személyazonosság-ellenőrző szolgáltatás ismételt időtúllépése; 18 jelentkezést érintett.

Relevant sources: incidents/bridge.md.

**Vector Standard**

> Az elakadást a külső személyazonosság-ellenőrző szolgáltatás ismétlődő időtúllépései okozták; 18 jelentkezést érintett. [Source: incidents/bridge.md#0]

Retrieved sources: incidents/bridge.md#0, projects/bridge.md#0, projects/bridge-north.md#0, vendors/clearid.md#0.

Source coverage: 100.0% · Time: 3.11 s · Evidence: Expected sources found · 1 model calls, 1 vector searches.

**Vector Multi-step**

> Az elakadást a külső személyazonosság-ellenőrző szolgáltatás ismétlődő időtúllépései okozták, és 18 jelentkezést érintett. [Source: incidents/bridge.md#0]

Retrieved sources: incidents/bridge.md#0, projects/bridge.md#0, projects/bridge-north.md#0, incidents/bridge-north.md#0, projects/bridge.md#6, vendors/clearid.md#1, incidents/bridge.md#2.

Source coverage: 100.0% · Time: 8.25 s · Evidence: Expected sources found · 4 model calls, 2 vector searches.

**Graph RAG**

> Az elakadást a külső személyazonosság-ellenőrző szolgáltatás ismétlődő időtúllépései okozták, és 18 jelentkezést érintett. [Source: incidents/bridge.md#0]

Retrieved sources: incidents/bridge.md#0.

Source coverage: 100.0% · Time: 4.42 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q04 · local — Mennyi időt engedélyeztek a Project Atlas visszaállítására a 2026. október 22-i üzemeltetési próbán?

Expected answer:

> 35 percet, a visszaállítás elrendelésétől az első új kérés elfogadásáig; az utólagos egyeztetés ezen kívül esik.

Relevant sources: meetings/atlas-operations.md.

**Vector Standard**

> 35 percet engedélyeztek a visszaállításra. [Source: meetings/atlas-operations.md#0]

Retrieved sources: projects/atlas-archive.md#0, projects/atlas.md#0, meetings/atlas-operations.md#0, vendors/dataloom.md#0.

Source coverage: 100.0% · Time: 2.34 s · Evidence: Expected sources found · 1 model calls, 1 vector searches.

**Vector Multi-step**

> 35 percet engedélyeztek a visszaállításra. [Source: meetings/atlas-operations.md#0]

Retrieved sources: projects/atlas.md#0, projects/atlas-archive.md#0, meetings/atlas-operations.md#0, vendors/dataloom.md#0.

Source coverage: 100.0% · Time: 6.34 s · Evidence: Expected sources found · 3 model calls, 1 vector searches.

**Graph RAG**

> A gráfos keresés ezt a kérdést még nem támogatja. Projektekre, vezetőikre, részlegekre, beszállítókra, incidensekre és az ideiglenes fiókokra lehet rákérdezni.

Retrieved sources: none.

Source coverage: 0.0% · Time: 3.47 s · Evidence: Question unsupported · 1 model calls.

Note: The question is outside the reviewed graph operations.

### Q05 · multi-hop — Melyik részlegen dolgozik a ClearID Kft. által támogatott projekt vezetője?

Expected answer:

> HR: a ClearID Kft. a Project Bridge szolgáltatója, a projektet Tamás Fekete vezeti, aki a HR-en dolgozik.

Relevant sources: vendors/clearid.md, projects/bridge.md, people/roles.md.

**Vector Standard**

> A források nem azonosítják a ClearID Kft. által támogatott projekt vezetőjét, ezért nem állapítható meg, melyik részlegen dolgozik. [Source: vendors/clearid.md#0]

Retrieved sources: vendors/clearid.md#0, vendors/clearid-audit.md#0, people/roles.md#3, people/roles.md#4.

Source coverage: 66.7% · Time: 1.98 s · Evidence: Some expected sources missing · 1 model calls, 1 vector searches.

Note: Some expected source documents were not retrieved.

**Vector Multi-step**

> A ClearID Kft. a Project Bridge-et támogatja, amelynek vezetője Tamás Fekete. Ő a HR részlegen dolgozik. [Source: vendors/clearid.md#0] [Source: people/roles.md#1]

Retrieved sources: vendors/clearid.md#0, vendors/clearid-audit.md#0, company.md#0, projects/atlas.md#0, projects/bridge.md#0, projects/bridge-north.md#0, vendors/greenwire.md#0, projects/beacon.md#0, people/roles.md#1, people/roles.md#4, people/roles.md#3, people/roles.md#0.

Source coverage: 100.0% · Time: 11.35 s · Evidence: Expected sources found · 5 model calls, 3 vector searches.

**Graph RAG**

> A projekt vezetője a HR-részlegen dolgozik. [Source: people/roles.md#1]

Retrieved sources: people/roles.md#1, projects/bridge.md#0, vendors/clearid.md#0.

Source coverage: 100.0% · Time: 4.11 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q06 · multi-hop — Ki vezeti a DataLoom adattárolási szolgáltatását használó projektet?

Expected answer:

> Nóra Váradi vezeti a Project Atlas Archive programot, amelyhez a DataLoom Zrt. archívumtárolást biztosít.

Relevant sources: vendors/dataloom.md, projects/atlas-archive.md.

**Vector Standard**

> Az archív tárolást használó projektet Nóra Váradi vezeti. [Forrás: projects/atlas-archive.md#0]

Retrieved sources: vendors/dataloom.md#0, projects/atlas-archive.md#0, projects/atlas.md#0, people/roles.md#3.

Source coverage: 100.0% · Time: 2.38 s · Evidence: Expected sources found · 1 model calls, 1 vector searches.

**Vector Multi-step**

> Nincs elegendő információ a korpuszban.

Retrieved sources: vendors/dataloom.md#0, projects/atlas-archive.md#0, projects/beacon-lab.md#0, projects/atlas-archive.md#6.

Source coverage: 100.0% · Time: 5.93 s · Evidence: Intermediate evidence unverified · 3 model calls, 1 vector searches.

Note: A search step returned no evidence or its extracted answer could not be verified after one retry.

**Graph RAG**

> A DataLoom adattárolási szolgáltatását használó projektet Nóra Váradi vezeti. [Source: projects/atlas-archive.md#0; vendors/dataloom.md#0]

Retrieved sources: projects/atlas-archive.md#0, vendors/dataloom.md#0.

Source coverage: 100.0% · Time: 4.96 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q07 · multi-hop — Mely beszállítók szolgáltatásait használja a 2026. szeptember 18-i API-incidens projektje, és mi a feladatuk?

Expected answer:

> A Project Atlas a NovaCloud Ltd. menedzselt API gateway hostingját és a SafeDesk Kft. riasztásfigyelését használja. A kapcsolat nem jelenti a beszállítók hibáztatását.

Relevant sources: incidents/atlas.md, vendors/novacloud.md, vendors/safedesk.md.

**Vector Standard**

> A források nem neveznek meg beszállítókat, ezért nem áll rendelkezésre elég információ annak megállapításához, hogy mely beszállítók szolgáltatásait használja a projekt, vagy mi a feladatuk. A beszámoló csak azt írja, hogy a 2026. szeptember 18-i Atlas API-incidenst egy telepítéskor bevezetett hibás átjáró-útválasztási szabály okozta. [Source: incidents/atlas.md#0]

Retrieved sources: projects/atlas.md#0, incidents/atlas.md#0, projects/atlas-archive.md#0, projects/beacon.md#0.

Source coverage: 33.3% · Time: 2.39 s · Evidence: Some expected sources missing · 1 model calls, 1 vector searches.

Note: Some expected source documents were not retrieved.

**Vector Multi-step**

> Nincs elegendő információ a korpuszban.

Retrieved sources: incidents/atlas.md#0, projects/atlas.md#0, projects/beacon.md#0, incidents/bridge.md#0, projects/atlas-archive.md#0, vendors/dataloom.md#0, vendors/safedesk.md#0.

Source coverage: 66.7% · Time: 10.65 s · Evidence: Intermediate evidence unverified · 4 model calls, 2 vector searches.

Note: A search step returned no evidence or its extracted answer could not be verified after one retry.

**Graph RAG**

> A 2026. szeptember 18-i API-incidens a Project Atlas projektet érintette. A projekt a NovaCloud Ltd. felügyelt API-átjáró-tárhelyszolgáltatását használja, amely az átjárókörnyezetet, a tanúsítványok karbantartását és a telepítési időszakokban elérhető eszkalációs útvonalat biztosítja. [Source: incidents/atlas.md#0] [Source: vendors/novacloud.md#0]
>
> A Project Atlas a SafeDesk Kft. riasztásfigyelő szolgáltatását is igénybe veszi; a forrás a feladatát riasztásfigyelésként nevezi meg. [Source: vendors/safedesk.md#0]

Retrieved sources: incidents/atlas.md#0, vendors/novacloud.md#0, vendors/safedesk.md#0.

Source coverage: 100.0% · Time: 6.18 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q08 · multi-hop — Melyik részlegen dolgozik a Project Atlas Archive vezetője?

Expected answer:

> Operations; a vezető Nóra Váradi.

Relevant sources: projects/atlas-archive.md, people/roles.md.

**Vector Standard**

> A Project Atlas Archive vezetője, Nóra Váradi az Operations részlegen dolgozik. [Source: people/roles.md#3]

Retrieved sources: projects/atlas-archive.md#0, projects/atlas.md#0, vendors/dataloom.md#0, people/roles.md#3.

Source coverage: 100.0% · Time: 1.55 s · Evidence: Expected sources found · 1 model calls, 1 vector searches.

**Vector Multi-step**

> A Project Atlas Archive vezetője, Nóra Váradi az Operations részlegen dolgozik. [Source: people/roles.md#3]

Retrieved sources: projects/atlas-archive.md#0, projects/atlas.md#0, vendors/dataloom.md#0, incidents/atlas.md#0, people/roles.md#3, people/roles.md#0, people/roles.md#4, emails/atlas-window.md#0.

Source coverage: 100.0% · Time: 8.04 s · Evidence: Expected sources found · 4 model calls, 2 vector searches.

**Graph RAG**

> A Project Atlas Archive vezetője, Nóra Váradi az Operations részlegen dolgozik. [Source: people/roles.md#3]

Retrieved sources: people/roles.md#3, projects/atlas-archive.md#0.

Source coverage: 100.0% · Time: 3.23 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q09 · global — Sorold fel a jóváhagyott projekteket a vezetőjükkel és a tervezett indulási dátumukkal!

Expected answer:

> Atlas — Nóra Varga, 2026-11-15; Atlas Archive — Nóra Váradi, 2027-02-12; Beacon — Réka Kiss, 2027-01-20; Beacon Lab — Péter Varga, 2026-12-15; Bridge — Tamás Fekete, 2026-12-01; Bridge North — Miklós Fekete, 2027-01-11.

Relevant sources: projects/atlas.md, projects/atlas-archive.md, projects/beacon.md, projects/beacon-lab.md, projects/bridge.md, projects/bridge-north.md.

**Vector Standard**

> - **Project Atlas** — vezetője Nóra Varga; tervezett indulás: **2026. november 15.** [Source: projects/atlas.md#0]
> - **Project Beacon** — vezetője Réka Kiss; tervezett indulás: **2027. január 20.** [Source: projects/beacon.md#0]
> - **Project Atlas Archive** — vezetője Nóra Váradi; tervezett indulás: **2027. február 12.** [Source: projects/atlas-archive.md#0]
>
> A források a projekteket nem nevezik kifejezetten „jóváhagyottnak”, ezért erről nem áll rendelkezésre elegendő információ.

Retrieved sources: projects/beacon.md#0, projects/atlas.md#0, people/roles.md#3, projects/atlas-archive.md#0.

Source coverage: 50.0% · Time: 2.53 s · Evidence: Some expected sources missing · 1 model calls, 1 vector searches.

Note: Some expected source documents were not retrieved.

**Vector Multi-step**

> Nincs elegendő információ a korpuszban.

Retrieved sources: projects/beacon.md#0, projects/atlas-archive.md#0, people/roles.md#3, projects/atlas.md#0.

Source coverage: 50.0% · Time: 5.40 s · Evidence: Intermediate evidence unverified · 3 model calls, 1 vector searches.

Note: A search step returned no evidence or its extracted answer could not be verified after one retry.

**Graph RAG**

> A forrásokban szereplő projektek, vezetőik és tervezett indulási dátumaik:
>
> | Projekt | Vezető | Tervezett indulás |
> |---|---|---|
> | Project Atlas | Nóra Varga | 2026-11-15 [Source: projects/atlas.md#0] |
> | Project Atlas Archive | Nóra Váradi | 2027-02-12 [Source: projects/atlas-archive.md#0] |
> | Project Beacon | Réka Kiss | 2027-01-20 [Source: projects/beacon.md#0] |
> | Project Beacon Lab | Péter Varga | 2026-12-15 [Source: projects/beacon-lab.md#0] |
> | Project Bridge | Tamás Fekete | 2026-12-01 [Source: projects/bridge.md#0] |
> | Project Bridge North | Miklós Fekete | 2027-01-11 [Source: projects/bridge-north.md#0] |
>
> A források nem jelölik meg kifejezetten, hogy mely projektek „jóváhagyottak”, ezért ezt a szűrést nem lehet megbízhatóan elvégezni.

Retrieved sources: projects/atlas-archive.md#0, projects/atlas.md#0, projects/beacon-lab.md#0, projects/beacon.md#0, projects/bridge-north.md#0, projects/bridge.md#0.

Source coverage: 100.0% · Time: 7.80 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q10 · global — Melyik beszállító mely projekteken dolgozik? Különítsd el az üzemeltetési és a hardveres feladatokat is!

Expected answer:

> NovaCloud: Atlas API gateway hosting; SafeDesk: Atlas és Beacon Lab riasztásfigyelés; GreenWire: Beacon és Bridge North hálózati eszközök és karbantartás; ClearID Kft.: Bridge személyazonosság-ellenőrzés; DataLoom: Atlas Archive archívumtárolás; ClearID Audit Kft.: Bridge North terminál-hozzáférési audit.

Relevant sources: vendors/novacloud.md, vendors/safedesk.md, vendors/greenwire.md, vendors/clearid.md, vendors/dataloom.md, vendors/clearid-audit.md.

**Vector Standard**

> A rendelkezésre álló források nem neveznek meg beszállítókat, és nem kapcsolják a beszállítókat konkrét projektekhez. A projektfelsorolás csak az érintett területeket sorolja fel: támogatási jegykezelés, munkavállalói beléptetés, irodai hálózat, iratmigráció, raktári betanítás és pénzügyi hálózati tesztkörnyezet. [Source: company.md#0]
>
> Ezért a beszállítók projektjeit, illetve az üzemeltetési és hardveres feladatok közötti különbséget a források alapján nem lehet megállapítani.

Retrieved sources: people/roles.md#3, people/roles.md#4, people/roles.md#0, company.md#0.

Source coverage: 0.0% · Time: 2.79 s · Evidence: Some expected sources missing · 1 model calls, 1 vector searches.

Note: Some expected source documents were not retrieved.

**Vector Multi-step**

> Nincs elegendő információ a korpuszban.

Retrieved sources: people/roles.md#3, vendors/greenwire.md#0, projects/beacon.md#0, projects/atlas-archive.md#0, company.md#0, people/roles.md#0.

Source coverage: 16.7% · Time: 6.59 s · Evidence: Intermediate evidence unverified · 4 model calls, 2 vector searches.

Note: A search step returned no evidence or its extracted answer could not be verified after one retry.

**Graph RAG**

> | Beszállító | Projekt(ek) és feladat |
> |---|---|
> | **ClearID Audit Kft.** | **Project Bridge North** — terminál-hozzáférések auditja; ez felülvizsgálati feladat, nem hardverszállítás. [Source: vendors/clearid-audit.md#0] |
> | **ClearID Kft.** | **Project Bridge** — személyazonosság- és dokumentum-ellenőrzés API-n keresztül; nem hardveres feladat. [Source: vendors/clearid.md#0] |
> | **DataLoom Zrt.** | **Project Atlas Archive** — kezelt archívumtárolás; a szolgáltatás dokumentumok megőrzését és felügyelt visszaállítását is támogatja. [Source: vendors/dataloom.md#0] |
> | **GreenWire Zrt.** | **Project Beacon** és **Project Bridge North** — hálózati kapcsolók és eszközkarbantartás, tehát hardveres feladatok. [Source: vendors/greenwire.md#0] |
> | **NovaCloud Ltd.** | **Project Atlas** — kezelt API-átjáró hosztolása, tanúsítvány-karbantartással; üzemeltetési feladat. [Source: vendors/novacloud.md#0] |
> | **SafeDesk Kft.** | **Project Atlas** és **Project Beacon Lab** — riasztásfigyelés; üzemeltetési feladat. [Source: vendors/safedesk.md#0] |
>
> A GreenWire feladatait sorolom a hardveres kategóriába; a többi felsorolt szolgáltatás nem hardverszállítás, hanem audit, ellenőrzés, tárolás, hosztolás vagy monitorozás.

Retrieved sources: vendors/clearid-audit.md#0, vendors/clearid.md#0, vendors/dataloom.md#0, vendors/greenwire.md#0, vendors/novacloud.md#0, vendors/safedesk.md#0.

Source coverage: 100.0% · Time: 7.13 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q11 · global — Milyen okok álltak a 2026 augusztusa és októbere közötti lezárt incidensek mögött?

Expected answer:

> Beacon: hibás switch firmware; Atlas: hibás gateway routing; Bridge North: betelt helyi nyomtatási kvóta; Bridge: személyazonosság-ellenőrzési időtúllépések; Beacon Lab: megmaradt duplikált riasztási feliratkozás; Atlas Archive: hibás dátumformátum a batch manifestben.

Relevant sources: incidents/beacon.md, incidents/atlas.md, incidents/bridge-north.md, incidents/bridge.md, incidents/beacon-lab.md, incidents/atlas-archive.md.

**Vector Standard**

> A lezárt incidensek okai:
>
> - **2026. augusztus – Project Beacon:** a csere hálózati kapcsoló hibás firmware-e okozta az időszakos hálózati megszakadásokat. [Source: incidents/beacon.md#0]
> - **2026. szeptember – Project Atlas:** a telepítés során bevezetett hibás átjáró-útválasztási szabály okozta az API-kiesést. [Source: incidents/atlas.md#0]
> - **2026. október – Project Bridge:** a külső személyazonosság-ellenőrző szolgáltatás ismétlődő időtúllépései okozták a bevezetési késéseket. [Source: incidents/bridge.md#0]
> - **2026. október – Project Atlas Archive:** a csomagjegyzék dátumformátuma nem volt kompatibilis az értelmezővel, ezért a dokumentumcsomagot elutasították. [Source: incidents/atlas-archive.md#0]

Retrieved sources: incidents/atlas-archive.md#0, incidents/beacon.md#0, incidents/atlas.md#0, incidents/bridge.md#0.

Source coverage: 66.7% · Time: 3.14 s · Evidence: Some expected sources missing · 1 model calls, 1 vector searches.

Note: Some expected source documents were not retrieved.

**Vector Multi-step**

> Nincs elegendő információ a korpuszban.

Retrieved sources: incidents/bridge.md#0, incidents/beacon.md#0, incidents/atlas-archive.md#0, emails/invoice-allocation.md#3.

Source coverage: 50.0% · Time: 4.47 s · Evidence: Intermediate evidence unverified · 3 model calls, 1 vector searches.

Note: A search step returned no evidence or its extracted answer could not be verified after one retry.

**Graph RAG**

> A 2026 augusztusa és októbere közötti lezárt incidensek okai:
>
> - **Augusztus 25. – Project Beacon:** hibás firmware egy cserehálózati kapcsolón. [Source: incidents/beacon.md#0]
> - **Szeptember 18. – Project Atlas:** telepítés közben bevezetett helytelen átjáró-útválasztási szabály. [Source: incidents/atlas.md#0]
> - **Szeptember 30. – Project Bridge North:** kimerült a helyi nyomtatási sor kvótája. [Source: incidents/bridge-north.md#0]
> - **Október 9. – Project Bridge:** ismétlődő időtúllépések a külső személyazonosság-ellenőrző szolgáltatásban. [Source: incidents/bridge.md#0]
> - **Október 16. – Project Beacon Lab:** egy képzés után bekapcsolva maradt egy duplikált riasztási feliratkozás. [Source: incidents/beacon-lab.md#0]
> - **Október 27. – Project Atlas Archive:** a kötegmanifestummal használt dátumformátum nem volt kompatibilis. [Source: incidents/atlas-archive.md#0]

Retrieved sources: incidents/atlas-archive.md#0, incidents/atlas.md#0, incidents/beacon-lab.md#0, incidents/beacon.md#0, incidents/bridge-north.md#0, incidents/bridge.md#0.

Source coverage: 100.0% · Time: 7.29 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

### Q12 · global — Milyen rendszeres felülvizsgálati és megőrzési határidőket kell betartani a külsős hozzáféréseknél, a beszállítóknál és a projektiratoknál?

Expected answer:

> Külsős fiók: legfeljebb 30 nap, megújítás 5 nappal lejárat előtt. Beszállítói kockázat: évente; szolgáltatási teljesítmény: negyedévente. Bizalmas projektirat: lezárás után 24 hónap; nyilvános oktatási anyag: visszavonás után 12 hónap.

Relevant sources: policies/access.md, policies/vendors.md, policies/data.md.

**Vector Standard**

> A rendelkezésre álló források nem írják le, milyen rendszeres felülvizsgálati határidők vonatkoznak a külsős hozzáférésekre vagy a beszállítókra, illetve meddig kell megőrizni a hozzájuk kapcsolódó iratokat.
>
> A projektiratokra a szabályzat szerint a bizalmas fájlokat a projekt lezárásától számított 24 hónapig kell megőrizni. A megőrzési idő kezdetét az esemény tulajdonosának kell rögzítenie; a dokumentum piszkozatának létrehozási dátuma nem indítja el az időszakot. [Source: policies/data.md#0]

Retrieved sources: people/roles.md#0, policies/data.md#0, projects/beacon.md#0, projects/atlas.md#6.

Source coverage: 33.3% · Time: 3.41 s · Evidence: Some expected sources missing · 1 model calls, 1 vector searches.

Note: Some expected source documents were not retrieved.

**Vector Multi-step**

> Nincs elegendő információ a korpuszban.

Retrieved sources: people/roles.md#0, vendors/clearid-audit.md#0, policies/data.md#0, projects/atlas.md#6.

Source coverage: 33.3% · Time: 4.22 s · Evidence: Intermediate evidence unverified · 3 model calls, 1 vector searches.

Note: A search step returned no evidence or its extracted answer could not be verified after one retry.

**Graph RAG**

> - **Külsős hozzáférések:** Az ideiglenes fiók kezdeti érvényessége legfeljebb **30 nap**. A megújítási kérelmet a lejárat előtt **5 nappal** kell benyújtani. [Source: policies/access.md#0]
> - **Beszállítók:** A beszállítói kockázatot **évente egyszer**, a szolgáltatási teljesítményt **negyedévente** kell felülvizsgálni. [Source: policies/vendors.md#0]
> - **Projektiratok:** A bizalmas projektfájlokat a projekt lezárásától számítva **24 hónapig** kell megőrizni. A megőrzési idő kezdő eseményét rögzíteni kell; a piszkozat létrehozási dátuma nem indítja el az időtartamot. [Source: policies/data.md#0]

Retrieved sources: policies/access.md#0, policies/data.md#0, policies/vendors.md#0.

Source coverage: 100.0% · Time: 6.47 s · Evidence: Expected sources found · 2 model calls, 2 graph queries.

## Missing evidence

- Q02, Vector Standard: Some expected source documents were not retrieved. Missing: policies/access.md.
- Q05, Vector Standard: Some expected source documents were not retrieved. Missing: projects/bridge.md.
- Q02, Vector Multi-step: A search step returned no evidence or its extracted answer could not be verified after one retry.
- Q06, Vector Multi-step: A search step returned no evidence or its extracted answer could not be verified after one retry.
- Q04, Graph RAG: The question is outside the reviewed graph operations. Missing: meetings/atlas-operations.md.

Showing 5 examples from 15 evidence gaps; all question-level details appear above.
