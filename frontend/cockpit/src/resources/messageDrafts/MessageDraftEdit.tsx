import {
  Edit,
  ReferenceInput,
  SelectInput,
  SimpleForm,
  TextInput,
  TopToolbar,
  ListButton,
  ShowButton,
} from "react-admin";

const MESSAGE_TYPE_CHOICES = [
  { id: "prospecting_email", name: "Prospecting Email" },
  { id: "linkedin_message", name: "LinkedIn Message" },
  { id: "follow_up_email", name: "Follow-Up Email" },
  { id: "training_proposal", name: "Training Proposal" },
  { id: "devops_proposal", name: "DevOps Proposal" },
  { id: "cybersecurity_proposal", name: "Cybersecurity Proposal" },
  { id: "academy_invitation", name: "Academy Invitation" },
  { id: "motivation_letter", name: "Motivation Letter" },
  { id: "cv_summary", name: "CV Summary" },
  { id: "internal_note", name: "Internal Note" },
];

const EditActions = () => (
  <TopToolbar>
    <ShowButton />
    <ListButton />
  </TopToolbar>
);

export const MessageDraftEdit = () => (
  <Edit actions={<EditActions />}>
    <SimpleForm>
      <ReferenceInput source="opportunity_id" reference="opportunities" />
      <ReferenceInput source="contact_id" reference="contacts" />
      <SelectInput
        source="message_type"
        label="Message Type"
        choices={MESSAGE_TYPE_CHOICES}
      />
      <TextInput source="language" />
      <TextInput source="subject" fullWidth />
      <TextInput source="body" multiline rows={8} fullWidth />
      <TextInput source="tone" />
      <TextInput source="review_notes" multiline rows={3} fullWidth />
    </SimpleForm>
  </Edit>
);
