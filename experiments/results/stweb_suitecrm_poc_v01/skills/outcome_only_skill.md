# SuiteCRM Operational Skill
## Planning and navigation
- When an operation will export records, create or change records, associate records, or make a bulk update, send a confirmation message before navigating or editing.
- For an export request without filter criteria, ask whether to export all records or a filtered subset, request confirmation, and then open the Contacts area.
- For a bulk lead-status change, state that the Leads list will be filtered by the current status and changed to the target status, request confirmation, and then open Leads.
- To work with an existing lead, case, or contact, open its module from the home area and select the target record from the module list.
- To create an account, open Accounts and activate the create-record form.

## Execution patterns
- In an account creation form, enter the account name, choose an assignee through a lookup by typing the value and pressing Enter, select the account type, and save.
- When updating a lead mobile number, open the record’s edit controls, select the status value Recycled, fill the mobile-number field, and save the record.
- When updating a case, open the case edit controls, fill the case text field, select Closed in the status control, and save when a save action is used.
- To associate a contact with an account, open the contact edit controls, activate the account-selection control, type the account value into the displayed lookup input, and wait after entry.

## Form entry and verification
- Use select-option interactions for demonstrated status and type controls, including Recycled, Closed, Pending Input, Prospect, and other displayed choices.
- After typing an account value into the contact association lookup, pause briefly rather than performing an additional demonstrated selection or save action.
- For import requests lacking a file name or path, request the file location and confirmation of the target module and field mapping before proceeding.

## Error recovery and stopping
- If filling a contact association control fails because the targeted element is not editable, click the related lookup control, fill the revealed input field, and pause briefly.
- After requesting confirmation for an export, bulk update, incomplete import, or case-closing action, stop at the confirmation or the demonstrated navigation point when no later action is shown.
