Phase 4 — React-admin Prospecting Cockpit
1. Context
The SORIA AI Prospecting Platform now has a validated backend foundation.
The backend already provides:
Company CRUDContact CRUDOpportunity CRUDMessageDraft workflow
The current validated manual flow is:
Company → Contact → Opportunity → MessageDraft → Human Review → sent_manually
The system already enforces the most important product rule:
No message is sent automatically.Every message must be created as a draft and reviewed by a human before any external action.
The next step is to make this backend usable through a clean internal interface.
Until now, validation has been done through:
curlpytestFastAPI runtime testsPostgreSQL test databaseGitHub Actions CI
This is technically valid, but not usable enough for daily prospecting.
Phase 4 introduces a dedicated administrative cockpit based on React-admin.

2. Phase 4 Objective
The goal of Phase 4 is to build a first usable internal web interface for the SORIA prospecting workflow.
This interface must allow the user to:
see companiessee contactssee opportunitiessee message draftscreate and edit business objectsreview message draftsapprove / reject / mark drafts as sent manuallyfollow the current state of the prospecting pipeline
The interface is not a public website.
It is an internal cockpit for managing the prospecting process.

3. Product Name
Recommended internal name:
SORIA Prospecting Cockpit
Possible UI title:
SORIA Cockpit
Possible repository/module naming:
frontend/cockpit
or:
apps/cockpit
Recommended for this project:
frontend/cockpit
Reason: the backend already exists under backend, so the repo remains simple:
soria-ai-prospecting-platform├── backend├── frontend│   └── cockpit├── docs├── kubernetes└── docker-compose.yml

4. Technology Choice
The chosen frontend technology is:
React-admin
React-admin is appropriate because the platform is data-oriented and workflow-oriented.
The current objects are structured resources:
companiescontactsopportunitiesmessage_drafts
Each resource needs:
listshowcreateeditfilteractionsstatus display
React-admin is designed for this kind of administrative interface.

5. Why React-admin Instead of a Custom Frontend
A fully custom React frontend would give maximum freedom, but it would require more time for:
routingformstablespaginationfiltersvalidation displayAPI integrationerror handlinglayoutpermissionsloading statesnotification system
React-admin already provides many of these patterns.
For Phase 4, the goal is not to create a beautiful marketing interface.
The goal is to create a practical cockpit that allows real use of the platform.
React-admin gives a good balance:
fast enough to buildstructured enough to maintaincustomizable enough for future evolutioncompatible with REST APIs

6. Architecture Principle
The cockpit must communicate only with the FastAPI backend.
It must not write directly to PostgreSQL.
Correct architecture:
React-admin Cockpit        ↓FastAPI REST API        ↓PostgreSQL
Forbidden architecture:
React-admin Cockpit        ↓Direct PostgreSQL write access
Reason:
The backend contains important business rules:
contact must belong to the same company as opportunitydraft cannot be edited after sent_manuallystatus transitions must follow the allowed workflowmessage cannot be sent automaticallyscore must stay between 0 and 100
If the frontend writes directly to the database, these rules can be bypassed.

7. Scope of Phase 4
Phase 4 must remain focused.
Included:
React-admin frontend bootstrapAPI data providerCompany pagesContact pagesOpportunity pagesMessageDraft pagesMessage review workflow actionsDashboard v1Local development configurationBasic frontend tests or build validationDocumentation
Excluded from Phase 4:
AI-generated messagesFrance Travail importHunter / contact enrichmentLinkedIn automationemail sendingautomatic outreachKubernetes deploymentJenkins pipelineauthentication / SSO hardeningmulti-user role managementadvanced analytics
Authentication can be prepared conceptually, but not implemented deeply in this phase unless already simple.

8. Main User Story
The main user story of this phase is:
As the SORIA operator,I want to manage prospecting opportunities through a cockpit,so that I can create companies, contacts, opportunities and message drafts,review them manually,and mark approved messages as manually sent,without using curl or touching the database directly.

9. Target Workflow in the UI
The cockpit must support this workflow:
1. Create or identify a company2. Add or identify a contact3. Create an opportunity4. Create a message draft from the opportunity5. Submit the draft for review6. Approve or reject the draft7. Mark the approved draft as sent manually8. Continue follow-up later
No external sending action is included.

10. Backend Resources Already Available
The frontend will rely on the following API resources.
Companies
GET    /api/v1/companiesPOST   /api/v1/companiesGET    /api/v1/companies/{company_id}PATCH  /api/v1/companies/{company_id}
Main usage:
list companiessearch companiescreate companyedit companyopen company detail
Contacts
GET    /api/v1/contactsPOST   /api/v1/contactsGET    /api/v1/contacts/{contact_id}PATCH  /api/v1/contacts/{contact_id}
Main usage:
list contactsfilter by companycreate contactedit contactopen contact detail
Opportunities
GET    /api/v1/opportunitiesPOST   /api/v1/opportunitiesGET    /api/v1/opportunities/{opportunity_id}PATCH  /api/v1/opportunities/{opportunity_id}
Main usage:
list opportunitiesfilter by status / priority / scorecreate opportunityedit opportunityopen opportunity detail
Message Drafts
GET    /api/v1/message-draftsPOST   /api/v1/message-draftsGET    /api/v1/message-drafts/{message_draft_id}PATCH  /api/v1/message-drafts/{message_draft_id}POST   /api/v1/message-drafts/{message_draft_id}/submit-reviewPOST   /api/v1/message-drafts/{message_draft_id}/approvePOST   /api/v1/message-drafts/{message_draft_id}/rejectPOST   /api/v1/message-drafts/{message_draft_id}/mark-sent-manually
Main usage:
create draftedit draft before review/sendingsubmit for reviewapproverejectmark as sent manually

11. React-admin Data Provider Strategy
React-admin expects a dataProvider.
The backend already returns list responses like:
{  "items": [],  "total": 0,  "skip": 0,  "limit": 50}
React-admin expects something closer to:
{  "data": [],  "total": 0}
So Phase 4 must implement a custom data provider that maps:
React-admin getList→ FastAPI GET /api/v1/{resource}?skip=&limit=&filters...FastAPI response items→ React-admin dataFastAPI response total→ React-admin total
The frontend must not force backend changes just to satisfy React-admin.
Recommended approach:
frontend/cockpit/src/dataProvider.ts
This file will translate React-admin calls to the existing FastAPI API.

12. Resource Mapping
React-admin resource names should match API resource names clearly.
Recommended:
companiescontactsopportunitiesmessage-drafts
The data provider must map these to:
/api/v1/companies/api/v1/contacts/api/v1/opportunities/api/v1/message-drafts

13. Pages to Build
13.1 Dashboard
The first dashboard should show operational indicators.
Minimum cards:
Total companiesTotal contactsTotal opportunitiesMessage drafts needing reviewApproved drafts not yet sent manuallyHigh-priority opportunities
If count endpoints do not exist yet, the dashboard can initially fetch list endpoints with filters and use total.
Example:
GET /api/v1/message-drafts?status=needs_review&limit=1
Use total from response.
The dashboard should also show:
Latest opportunitiesLatest message drafts needing review

13.2 Companies Page
The Companies page must include:
list viewsearch filterstatus filtercompany_type filtercountry filtercreate formedit formshow page
Important displayed columns:
namecompany_typestatuscitycountrydomaincreated_atupdated_at
Important form fields:
nameslugwebsite_urldomaincompany_typesectorsize_labelemployee_countcityregioncountrysourcesource_urlnotesstatus
Related data to show later:
contacts linked to this companyopportunities linked to this company

13.3 Contacts Page
The Contacts page must include:
list viewfilter by companysearch filtercontact_type filteremail_verification_status filteropt_out filtercreate formedit formshow page
Important displayed columns:
full_namecompany_idrole_titleemailcontact_typeemail_verification_statusis_primaryopt_outcreated_at
Important form fields:
company_idfirst_namelast_namefull_namerole_titleemailphonelinkedin_urlcontact_typesourcesource_urlemail_verification_statusis_primaryopt_outnotes
For company_id, the UI should use a reference input to select a company.

13.4 Opportunities Page
The Opportunities page is central.
It must include:
list viewstatus filterpriority filteropportunity_type filtercompany filtercontact filtermin_score filtersearch filtercreate formedit formshow page
Important displayed columns:
titlecompany_idcontact_idopportunity_typestatuspriorityscorelocationcreated_atupdated_at
Important form fields:
company_idcontact_idoffer_idacademy_resource_idtitleopportunity_typedescriptiondetected_needsourcesource_urlsource_published_atlocationlanguagestatuspriorityscorerecommended_landing_pagenext_actionnotes
The show page should also provide a visible action:
Create Message Draft
This action can pre-fill:
opportunity_idcontact_idlanguagemessage_type

13.5 Message Drafts Page
This is the most important page for the current workflow.
It must include:
list viewstatus filteropportunity filtercontact filtermessage_type filterlanguage filtersearch filtercreate formedit formshow pageworkflow action buttons
Important displayed columns:
subjectstatusmessage_typelanguageopportunity_idcontact_idgenerated_byapproved_atsent_atcreated_atupdated_at
Important form fields:
opportunity_idcontact_idmessage_typelanguagesubjectbodytonegenerated_bymodel_nameprompt_versionreview_notes
The UI must not allow direct arbitrary status edits.
Status must be changed through action buttons:
Submit for ReviewApproveRejectMark Sent Manually

14. MessageDraft Workflow UI Rules
The UI must show buttons according to status.
If status is draft
Allowed:
EditSubmit for Review
Not allowed:
ApproveRejectMark Sent Manually
If status is needs_review
Allowed:
ApproveReject
Not allowed:
Edit status directlyMark Sent Manually
Editing content at this stage should be considered carefully.
Recommended: allow editing only by returning to draft/rejected flow in a later phase.
For Phase 4, follow backend behavior.
If status is approved
Allowed:
Mark Sent Manually
Not allowed:
Edit bodyApprove againReject
If status is rejected
Allowed:
EditSubmit for Review
If status is sent_manually
Allowed:
View only
Not allowed:
EditApproveRejectSubmit for Review
If status is archived
Allowed:
View only

15. Design Requirements
The cockpit must be practical and readable.
Priorities:
claritystatus visibilityfast navigationsafe actionsminimal clicksstrong filtering
Each status should be visually recognizable.
Suggested status display:
draft              greyneeds_review       orangeapproved           greenrejected           redsent_manually      bluearchived           dark grey
The UI should clearly separate:
data entryreviewvalidated/sent records

16. Safety Requirements
The cockpit must protect the workflow.
Frontend safety rules:
do not expose sent_by_systemdo not expose direct status update in MessageDraft edit formdo not show Mark Sent Manually unless status is approveddo not show Approve unless status is needs_reviewdo not show Reject unless status is needs_reviewdo not show Submit Review unless status is draft or rejected
Backend is still the source of truth.
Even if the frontend has a bug, backend must reject invalid transitions.

17. Authentication Strategy
Authentication is not the main scope of Phase 4, but the cockpit must be designed with future authentication in mind.
Phase 4A can use:
local development without auth
or:
simple reverse-proxy protection
Future target:
Keycloak / SSO
Possible future roles:
adminoperatorreviewerreadonly
For now, do not over-engineer authentication.
The cockpit should not be publicly exposed without protection.

18. API Configuration
The frontend must read the backend API URL from an environment variable.
Recommended:
VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1
For future production:
VITE_API_BASE_URL=https://api-prospecting.example.com/api/v1
The frontend must not hardcode production URLs.

19. Local Development Target
Recommended commands:
cd frontend/cockpitnpm installnpm run dev
Backend local run:
cd backenduv run uvicorn app.main:app --host 127.0.0.1 --port 8001
Frontend local URL:
http://127.0.0.1:5173

20. Recommended Frontend Structure
Suggested structure:
frontend/cockpit├── package.json├── vite.config.ts├── tsconfig.json├── index.html├── src│   ├── main.tsx│   ├── App.tsx│   ├── dataProvider.ts│   ├── config.ts│   ├── resources│   │   ├── companies│   │   │   ├── CompanyList.tsx│   │   │   ├── CompanyCreate.tsx│   │   │   ├── CompanyEdit.tsx│   │   │   └── CompanyShow.tsx│   │   ├── contacts│   │   │   ├── ContactList.tsx│   │   │   ├── ContactCreate.tsx│   │   │   ├── ContactEdit.tsx│   │   │   └── ContactShow.tsx│   │   ├── opportunities│   │   │   ├── OpportunityList.tsx│   │   │   ├── OpportunityCreate.tsx│   │   │   ├── OpportunityEdit.tsx│   │   │   └── OpportunityShow.tsx│   │   └── messageDrafts│   │       ├── MessageDraftList.tsx│   │       ├── MessageDraftCreate.tsx│   │       ├── MessageDraftEdit.tsx│   │       ├── MessageDraftShow.tsx│   │       └── MessageDraftActions.tsx│   └── dashboard│       └── Dashboard.tsx

21. Data Provider Requirements
The custom data provider must support at least:
getListgetOnecreateupdate
Delete is not required.
React-admin may expect delete, but it can be disabled or implemented as unsupported.
For list endpoints:
React-admin input:
pagination.pagepagination.perPagefiltersort
Backend expects:
skiplimitfilters
Mapping:
skip = (page - 1) * perPagelimit = perPage
FastAPI response:
{  "items": [],  "total": 0,  "skip": 0,  "limit": 50}
React-admin response:
{  "data": [],  "total": 0}

22. Special Data Provider Actions
React-admin standard data provider methods are not enough for workflow actions.
Custom calls are needed for:
submit-reviewapproverejectmark-sent-manually
Recommended implementation:
messageDraftWorkflowApi.ts
or inside:
resources/messageDrafts/MessageDraftActions.tsx
These functions call:
POST /message-drafts/{id}/submit-reviewPOST /message-drafts/{id}/approvePOST /message-drafts/{id}/rejectPOST /message-drafts/{id}/mark-sent-manually
After each successful action, the UI should refresh the record.

23. Phase 4 Acceptance Criteria
Phase 4 is accepted when:
React-admin cockpit starts locallyBackend API URL is configurableCompanies can be listed, created, edited and viewedContacts can be listed, created, edited and viewedOpportunities can be listed, created, edited and viewedMessageDrafts can be listed, created, edited and viewedMessageDraft workflow buttons workInvalid workflow transitions are not exposed in the UIBackend still rejects invalid transitionsDashboard shows useful countsFrontend build passesBackend tests still passNo email sending is implementedNo AI call is implementedNo external integration is added

24. Tests and Validation
Minimum validation commands for Phase 4:
Backend:
cd backenduv run pytestuv run ruff check .uv run python -c "from app.main import app; print(app.title)"
Frontend:
cd frontend/cockpitnpm installnpm run build
If tests are added:
npm test
Runtime validation:
Run FastAPI locallyRun React-admin locallyCreate CompanyCreate ContactCreate OpportunityCreate MessageDraftSubmit ReviewApproveMark Sent ManuallyVerify final status

25. Git Strategy
Use a dedicated branch:
git checkout maingit pull origin maingit checkout -b phase-4-react-admin-cockpit
After implementation:
git add frontend/cockpit docs README.mdgit commit -m "feat: add React-admin prospecting cockpit"git push -u origin phase-4-react-admin-cockpit
Then create a Pull Request:
phase-4-react-admin-cockpit → main
CI must remain green.

26. OpenProject Mapping
This phase should be tracked under a new work package:
WP-15 — React-admin Prospecting Cockpit
Suggested description:
Créer un cockpit interne basé sur React-admin pour exploiter le backend SORIA AI Prospecting Platform. Le cockpit doit permettre de gérer les entreprises, contacts, opportunités et brouillons de messages, avec un workflow de validation humaine avant tout marquage comme envoyé manuellement.
Suggested subtasks:
WP-15.1 — Définir la spécification UI du cockpitWP-15.2 — Initialiser le frontend React-adminWP-15.3 — Implémenter le dataProvider FastAPIWP-15.4 — Créer les pages CompaniesWP-15.5 — Créer les pages ContactsWP-15.6 — Créer les pages OpportunitiesWP-15.7 — Créer les pages MessageDraftsWP-15.8 — Implémenter les actions de workflow MessageDraftWP-15.9 — Créer le dashboard v1WP-15.10 — Valider le build frontend et les tests backend
Milestone suggestion:
M7 — React-admin cockpit opérationnel
If you prefer not to create a new milestone, it can be attached to:
M3 — MVP manuel opérationnel
But since M3 is already completed, I recommend creating a new milestone:
M7 — Cockpit interne React-admin

27. Future Phases After React-admin
Once the cockpit exists, the next phases become easier.
Possible future phases:
Scoring v1France Travail import v1Contact enrichment providerAI draft generationOpenProject syncKubernetes deploymentKeycloak authenticationMonitoring and backups
The cockpit will become the place where imported or generated data is reviewed before any action.

Final Decision
Phase 4 will build:
SORIA Prospecting Cockpit
with:
React-adminFastAPI REST APIPostgreSQL through backend onlyManual workflow controlNo automatic sendingNo AI integration yetNo external integration yet
The immediate next implementation step is:
Create branch phase-4-react-admin-cockpitInitialize frontend/cockpit with React-admin + ViteBuild custom FastAPI dataProviderImplement Dashboard + Companies + Contacts + Opportunities + MessageDrafts
