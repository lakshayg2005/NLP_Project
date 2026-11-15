# Hugging Face Space deployment

The dashboard supports a Live audit only mode for a public demo. The trained model
artifacts are not in this repository, and publishing them or creating a public Space
requires a Hugging Face account with write access.

## Prepare the model repositories

Upload the SetFit model folder produced by `scripts/train_setfit.py` and the span model
folder produced by `scripts/train_span_extractor.py` to separate Hugging Face model repos.
Make them public if the demo should work without a Hugging Face token. Keep the repositories
private and configure a `HF_TOKEN` Space secret if access should be restricted.

## Create the Space

1. Create a new Space and choose the **Docker** SDK.
2. Copy this project into the Space repository.
3. Set `HF_SPACE=true`, `SETFIT_MODEL_REPO=<owner/model>`, and
   `SPAN_MODEL_REPO=<owner/model>` as Space variables. Set `HF_TOKEN` as a secret for
   private model repositories.
4. Set the Space app port to `8501` and use the Streamlit command from the Compose
   `dashboard` service as the container command.
5. Push the Space repository. On first launch, model files are downloaded from the Hub;
   later launches use the Hub cache.

`HF_SPACE=true` leaves only the Live audit page in the navigation. Local model folders take
precedence over Hub IDs. If either Hub model repository is omitted, the existing zero-shot
or regex fallback remains available.
