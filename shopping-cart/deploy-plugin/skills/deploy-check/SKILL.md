---
name: deploy-check
description: "Deploy the shopping cart app and verify it's working"
user-invocable: true
allowed-tools:
  - Bash
  - Read
---

Deploy and verify the shopping cart application:

1. Run ./deploy.sh from the project root
2. Wait for the deployment to complete
3. Report the API URL and Frontend URL from the output
4. Test the /api/products endpoint to confirm it returns data
5. Report success or failure with details
