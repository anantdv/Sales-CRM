# Sales CRM

Phase 1 enterprise CRM app for Frappe/ERPNext v16.

The app adds CRM-owned lead, account profile, opportunity, qualification,
pipeline, stage history, relationship, and activity models while linking back
to ERPNext transactional records.

## Install

From the bench:

```bash
bench get-app /path/to/sales_crm
bench --site blc.advtinni.com install-app sales_crm
bench --site blc.advtinni.com migrate
```

Seed demo data:

```bash
bench --site blc.advtinni.com execute sales_crm.demo.demo_data.create_demo_data
```
