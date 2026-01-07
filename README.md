### Database setup
Run these commands to convert the CSV outputs to a PostgreSQL database (named "cytokines" by default).
Note that if the table has already been created, it will not be changed.
```
python server/import_csv.py --file path/to/data.csv
```

Optionally, push to Supabase for hosting:
Create a `server/.env` file with the following variables (see your project page to find this info):
```
DATABASE_URL=postgresql://<user>@localhost:5432/cytokines
SUPABASE_URL=<insert supabase connection string>
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_KEY=...
```
```
pg_dump -Fc -U <user> -d cytokines > cytokines.dump

pg_restore \
  --dbname= <insert supabase connection string>
  --jobs=1 \
  --format=directory \
  --no-owner \
  --no-privileges \
  --verbose \
  cytokines.dump 2>&1 | perl -ne 'print scalar(localtime), " ", $_' | tee -a restore.log
```

### Run app
Start FastAPI server:
```
python server/app.py
```

Start React frontend: 
```
cd client
npm run dev
```

