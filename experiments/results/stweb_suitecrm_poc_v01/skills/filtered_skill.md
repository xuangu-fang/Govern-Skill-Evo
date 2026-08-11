# SuiteCRM Operational Skill
## Planning and navigation
- For a case update, navigate from the home area to Cases, open the target record from the list, and enter its edit view.
- For a contact-account association, navigate from the home area to Contacts, open the target contact, enter its edit view, and open the account relation control.

## Execution patterns
- When an export request provides no filter criteria, ask whether to export all records or a filtered subset and request confirmation before proceeding.
- When creating a case with description and type omitted, ask whether to create it using only the supplied fields.
- Before closing a case, state the intended notes-and-closure action and ask for confirmation.
- Before a bulk lead status update, describe filtering leads by their current status, identify the target status, and ask whether to proceed.
- Before associating a contact with an account, explicitly ask the user to confirm the requested association.

## Form entry and verification
- In a case edit view, enter the resolution notes in the notes field and select the requested closed status.
- In a contact edit view, activate the account relation input and fill it with the requested account value.
- After filling the account relation input, wait briefly for the interface response.

## Error recovery and stopping
- When resolution notes have been entered but closure has not yet been selected, ask whether to close the case and stop at that confirmation request.
- After navigating only to a module following a confirmation request, do not infer additional form actions that were not performed in the observed sequence.
