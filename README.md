# Sales CRM

Enterprise Sales CRM app for Frappe/ERPNext v16.

## Install

```bash
cd ~/courts-frappe-v16
bench get-app https://github.com/anantdv/Sales-CRM.git
bench --site blc.advtinni.com install-app sales_crm
bench --site blc.advtinni.com migrate
bench --site blc.advtinni.com clear-cache
bench build --app sales_crm
bench restart
```
