# RiskRules

- Only resource inventory and plan generation are allowed.
- Do not create, delete, expand or shrink, migrate, bind or unbind any resources.
- Secret only allows recording existence, name and purpose, and does not output sensitive values.
- The project_id, AK/SK, token, and certificate in the output must be desensitized or omitted.
- All execution actions are put into the subsequent manual confirmation list.