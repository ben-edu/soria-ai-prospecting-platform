import {
  Create,
  ReferenceInput,
  required,
  SelectInput,
  SimpleForm,
  TextInput,
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

export const MessageDraftCreate = () => (
  <Create>
    <SimpleForm>
      <ReferenceInput
        source="opportunity_id"
        reference="opportunities"
        validate={required()}
      />
      <ReferenceInput source="contact_id" reference="contacts" />
      <SelectInput
        source="message_type"
        label="Message Type"
        choices={MESSAGE_TYPE_CHOICES}
        defaultValue="prospecting_email"
      />
      <TextInput source="language" defaultValue="fr" />
      <TextInput source="subject" fullWidth />
      <TextInput
        source="body"
        validate={required()}
        multiline
        rows={8}
        fullWidth
      />
      <TextInput source="tone" />
      <TextInput source="generated_by" defaultValue="manual" />
    </SimpleForm>
  </Create>
);
