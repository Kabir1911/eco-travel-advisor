# Eco-Travel Advisor

BSBI — Advanced Conversational UI Design & Chatbot Development  
Student: Sahil Goraksh Arjun  
Repository: https://github.com/Kabir1911/eco-travel-advisor

A coursework prototype for comparing travel cost and estimated carbon emissions on a demonstration route from Frankfurt to Berlin. It uses Rasa Open Source 3.6.21, DIETClassifier, spaCy English features, custom Python actions and a React interface.

## Scope

- Collect destination, origin, dates, budget and sustainability preference.
- Compare fictional coach, rail and flight options using price/carbon weights.
- Browse fictional hotels in a carousel and check accommodation costs against the budget.
- Retrieve Climatiq carbon estimates, Open-Meteo weather and Frankfurter currency rates.
- Display cached destination information from OpenStreetMap services and Wikipedia, separately from fictional priced options.
- Offer clarification buttons and prepare trip details/conversation history for handover. No advisor service receives the information.

Deployment is local through Docker Compose. GitHub hosts the source and evidence; it is not a live chatbot website. No cloud deployment is claimed.

## Requirements

- Git and Docker Desktop, running Linux containers (WSL2 on the tested Windows setup).
- Internet access for image downloads and external APIs.
- A Climatiq API key with access to the factors used by the actions.
- Free local ports 5005 and 8000.

The commands below use **Windows Command Prompt**, not PowerShell. Run each from the project root unless stated otherwise. Docker provides Python and spaCy; a local Python virtual environment or Node installation is not required for the basic Docker setup. The Windows requirements files record the development environment and are not the Linux container installation method.

## First-time setup

### 1. Clone

```bat
git clone https://github.com/Kabir1911/eco-travel-advisor.git
cd eco-travel-advisor
```

### 2. Configure the API key

For a fresh clone only:

```bat
copy .env.example .env
```

Edit `.env` locally so it contains:

```dotenv
CLIMATIQ_API_KEY=YOUR_OWN_KEY_HERE
```

Replace the placeholder with your own key. Do not commit `.env` or paste keys into source files. Compose requires this variable before it starts. `.env.example` must contain only a placeholder. Do not overwrite an existing configured `.env`.

### 3. Train the model

Trained model archives are excluded from Git. Create the output folder:

```bat
mkdir models
```

If it already exists, continue. Run the following as one command:

```bat
docker run --rm -v "%cd%/config.yml:/app/config.yml:ro" -v "%cd%/domain.yml:/app/domain.yml:ro" -v "%cd%/data:/app/data:ro" -v "%cd%/models:/app/models" rasa/rasa:3.6.21-spacy-en train --fixed-model-name eco-entity-context
```

Wait for successful training and confirm `models/eco-entity-context.tar.gz` exists. Retraining can produce different evaluation results; the committed results describe the tested model used during development.

### 4. Start

```bat
docker compose up -d --build
docker compose logs --tail=30 rasa actions
```

Wait for Rasa's `Rasa server is up and running` message and the action endpoint startup message. Starting a container does not mean model loading has finished.

Open **http://localhost:8000**. This exact frontend origin is configured in CORS. The browser calls the REST endpoint on `http://127.0.0.1:5005`. The action server is reached internally at `http://actions:5055/webhook`.

The frontend and Rasa host ports bind to the laptop's loopback address. This configuration is not intended for direct public exposure.

### 5. Stop

From the same project folder:

```bat
docker compose down
```

## Demonstration flow

Use the website chat, not Command Prompt, for these messages:

1. Click **Plan a trip**, then **Berlin**.
2. Enter `from 2026-11-10 to 2026-11-15`.
3. Enter `My budget is 500 euros`.
4. Choose **Balance cost and sustainability**.
5. Click **Hotels** and browse the three cards using Next/Previous.
6. Enter `I am travelling from Frankfurt` to display transport options.
7. Try Destination guide, Weather and Convert budget to INR.
8. Click Request advisor and expand the prepared details.

The example dates are demonstration inputs. Hotel prices and transport availability are not live bookings. Weather covers the dates actually displayed, not necessarily the planned trip dates.

Additional checks: budget of 0 should be rejected; a return date before departure should be rejected; a EUR 100 budget for five nights should produce the accommodation shortfall message. Three consecutive `/nlu_fallback` messages exercise the clarification/handover flow directly, but do not test natural-language recognition.

## Project layout

| Path | Purpose |
|---|---|
| `config.yml` | NLU pipeline and dialogue policies |
| `domain.yml` | Intents, entities, slots, responses and action registration |
| `data/` | NLU examples, rules and training stories |
| `actions/actions.py` | Validation, external-service integration, ranking and handover |
| `frontend/src/` | React source and styles |
| `frontend/app.js`, `frontend/app.css` | Bundled assets served by Docker |
| `mock_data/travel_options.json` | Fictional priced hotels and routes |
| `cache_data/berlin.json` | Cached external destination information and attribution |
| `api_examples/` | Lecturer-provided reference examples |
| `tests/` | NLU and dialogue test inputs |
| `results/` | Evaluation outputs from several development stages |
| `compose.yml`, `Dockerfile.actions` | Local container setup |

Cached destination data is included, so it does not need to be fetched on startup. `fetch_destination_data.py` is an optional data-refresh utility; review its dependencies and service user-agent requirements before running it.

## Evaluation

Recorded final development results, 6 October 2026:

| Measure | Result |
|---|---:|
| Intent accuracy | 35/36 (97.22%) |
| Intent macro F1 | 0.9833 |
| DIET entity macro F1 | 1.0000 |
| DIET entity micro F1 | 1.0000 |
| DIET entity weighted F1 | 1.0000 |
| Correct dialogue action predictions | 57/57 |
| Dialogue action F1 | 1.0000 |

These results belong to `eco-entity-context.tar.gz`.
NLU evidence is in `results/nlu_entity_context`; dialogue evidence
is in `results/core_entity_context`.

The 36-example NLU set was repeatedly used to guide development,
so it is a development evaluation set, not an untouched held-out test.
These scores do not establish performance on unseen conversations.
Core tests evaluate action selection from supplied intents; they do
not independently verify live API responses or custom-action execution.
Earlier evaluation folders are retained for comparison.

Final evidence: `results/core_entity_context` and `results/nlu_entity_context`. Earlier folders, including `core_final_ui` and `nlu_final_ui`, contain results from previous model versions.

Intent and entity confusion matrices are `intent_confusion_matrix.png` and `DIETClassifier_confusion_matrix.png`. JSON reports and error files are stored alongside them.

These are small development tests, reused during iteration, not an untouched independent benchmark or cross-validation. The 36 NLU examples cover 12 intents, not every added feature. The Core tests check dialogue predictions from supplied intents; they do not independently execute and verify every custom action or external API.

Two transport requests were confused with weather or destination requests. DIET labelled return-date tokens as departure-date tokens in three test messages and missed a budget in one message. Return-date F1 was 0.0. Custom date and budget parsers mitigate extraction errors when the correct intent invokes them; they do not change the DIET evaluation scores. The Transport button supplies an explicit intent.

### Run tests without replacing recorded evidence

Create a results folder if absent. Run each command on one line:

```bat
docker run --rm -v "%cd%/models:/app/models:ro" -v "%cd%/tests:/app/tests:ro" -v "%cd%/results:/app/results" rasa/rasa:3.6.21-spacy-en test core --model /app/models/eco-entity-context.tar.gz --stories /app/tests/test_stories.yml --out /app/results/core_recheck --successes
```

```bat
docker run --rm -v "%cd%/models:/app/models:ro" -v "%cd%/domain.yml:/app/domain.yml:ro" -v "%cd%/tests:/app/tests:ro" -v "%cd%/results:/app/results" rasa/rasa:3.6.21-spacy-en test nlu --model /app/models/eco-entity-context.tar.gz --nlu /app/tests/test_nlu.yml --out /app/results/nlu_recheck
```

## Data and limitations

Transport options and hotel prices are fictional. Transport estimates are one passenger, one-way. Accommodation checks exclude transport, meals and other costs and cannot establish total-trip affordability. No bookings, schedules or live availability are provided.

Transport comparison uses Germany/UBA/2024 factors: electric long-distance train, general bus as a coach proxy, and domestic flight including radiative forcing. Route distances are illustrative. The standalone train calculator uses a different Germany/ADEME/2020 reference factor; its outputs should not be treated as the same methodology.

Ranking combines min-max-normalised price and carbon: balanced 50/50, environment preference 20/80, price preference 80/20. These are design choices, not scientifically calibrated utility weights. Carbon colours describe relative thirds of the displayed emissions range, not certified sustainability ratings. Missing estimates are not zero emissions.

Mapped hotels are distinct from fictional priced hotels. Map eco tags and hotel certification are unverified. Access-point counts do not establish service frequency or accessibility. Cached descriptions may become outdated. Currency rates are dated reference rates, not bank quotes; budgets remain in euros.

Handover is `prepared_only`: no real advisor receives messages. New conversation creates a new session identifier and does not itself delete server history. Avoid entering sensitive personal data. No persistent conversation database is configured in this local prototype.

## Sources and acknowledgements

- Rasa Open Source and Rasa SDK: https://rasa.com/
- spaCy: https://spacy.io/
- React: https://react.dev/ — bundled dependency licence notices are in `frontend/THIRD_PARTY_LICENSES.txt`.
- Climatiq: https://www.climatiq.io/ — factor-specific sources are shown in the application.
- OpenStreetMap contributors: https://www.openstreetmap.org/copyright — destination map data, ODbL; geocoding via Nominatim and queries via Overpass.
- Wikipedia Berlin article: https://en.wikipedia.org/wiki/Berlin — cached description, attribution and retrieval timestamp retained in the cache and UI. This data attribution is not a scholarly reference for the assignment report.
- Open-Meteo: https://open-meteo.com/ — weather attribution displayed in the UI.
- Frankfurter: https://frankfurter.dev/ — dated currency reference rates.
- Lecturer-provided API worksheets/examples retained in `api_examples/` and adapted for the coursework prototype.
- AI assistance was used during implementation and debugging; testing and limitations are documented rather than presented as production guarantees.

## Troubleshooting

- **No response:** check Docker Desktop, then `docker compose ps -a` and the Rasa/action logs. Wait for model loading to complete.
- **Model missing:** train using the exact output name above before starting Compose.
- **Port in use:** stop other standalone Rasa servers or another copy of this Compose project using the same ports.
- **Carbon API failure:** check the local key, network access and factor permissions. Never post the key with diagnostic logs.
- **Old interface after edits:** press Ctrl+F5. Rebuilding from React source requires Node.js; run `npm ci` then `npm run build` inside `frontend`.
- **Changed Python actions:** run `docker compose up -d --build --force-recreate actions rasa`.
- **Changed training data/domain:** retrain and restart Rasa. Changing code on disk does not retrain the model.

A clean-clone setup check should be recorded after following these instructions; it is not claimed as completed by this README.
