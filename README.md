# Cytokine Effects Knowledge Base
Webpage: https://mpark20.github.io/cytokine-effects-kb/

Paper: TBD


## Internal Setup Instructions
### Database setup
Run these commands to convert the CSV outputs to a PostgreSQL database (named "cytokines" by default).
```bash
python server/import_db.py --file path/to/data.csv
```

Note that if the table has already been created, it will not be changed. You may need to manually delete:
```
psql -U <username> postgres
DROP DATABASE cytokines 
```

If production-ready, deploy to Supabase:
Create a `server/.env` file with the following variables (see your project page to find this info):
```
DATABASE_URL=postgresql://<user>@localhost:5432/cytokines
SUPABASE_URL=<insert supabase connection string>
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_KEY=...
```
```bash
pg_dump -Fc -U <user> -d cytokines > cytokines.dump

pg_restore \
  --dbname=<insert supabase connection string>
  --jobs=1 \
  --format=directory \
  --no-owner \
  --no-privileges \
  --verbose \
  cytokines.dump 2>&1 | perl -ne 'print scalar(localtime), " ", $_' | tee -a restore.log
```

### Run app locally
First, set `API_BASE_URL = "http://localhost:8000"` at the top of `client/components/CytokineKnowledgebase.jsx`. This ensures local changes are reflected on the frontend.

Now, launch the app
```bash
# backend
cd server
python /main_local.py

# frontend
cd client
npm install
npm run dev
```

### Deploy
IMPORTANT! Make sure `API_BASE_URL = "https://cytokine-effects-kb-production.up.railway.app"` in `client/components/CytokineKnowledgebase.jsx` before pushing to main. The deployment will break if this is mistakenly set to localhost.

Backend changes deploy automatically to Railway when changes are pushed to the `main` branch

Finally, we can deploy frontend changes to GitHub Pages:
`npm run deploy -- -m "insert deployment message"`
