# TrustMesh Deployment Guide

## Render Deploy Hook

The CI pipeline (`.github/workflows/deploy.yml`) deploys to Render on every push to `master` using a deploy hook.

### Setting up the deploy hook

1. In the [Render Dashboard](https://dashboard.render.com), navigate to your web service.
2. Go to **Settings > Deploy Hooks**.
3. Click **Generate Deploy Hook** and copy the generated URL.
4. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
5. Add a new repository secret named `RENDER_DEPLOY_HOOK_URL` with the copied URL as its value.

The `deploy` job in `deploy.yml` reads this secret and triggers a deploy by sending a `POST` request to the hook URL. If the secret is absent, the step logs a message and exits cleanly — it does not fail the workflow.

## Branch Protection

To enforce the green-check gate (tests must pass before deploy):

1. Go to **GitHub repo > Settings > Branches > Add branch protection rule**.
2. Set **Branch name pattern** to `master`.
3. Under **Protect matching branches**, enable **Require status checks**.
4. Search for and select the **test** status check (the job name from `deploy.yml` / `pytest.yml`).
5. Optionally enable **Require branches to be up-to-date** and **Include administrators**.

Once enabled, every PR to `master` must pass the `test` job before it can be merged, and every push to `master` that passes tests triggers an automatic deploy.
