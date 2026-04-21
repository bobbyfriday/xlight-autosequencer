# dist/

Vite build output. **Committed to git** so that `pip install xlight-autosequencer` works
without requiring Node on the end-user's machine.

Refresh before every release:
```bash
cd src/review/frontend
npm run build
git add dist/
git commit -m "chore: refresh frontend dist"
```

See specs/051-x-onset-frontend/quickstart.md §4 for details.
