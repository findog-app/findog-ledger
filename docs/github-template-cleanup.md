# Przygotowanie repozytorium do publikacji na GitHubie

Analiza pozostałości po FastAPI full-stack template i elementów wymagających uporządkowania przed pierwszym publicznym pushem.

## Priorytet przed pierwszym pushem

### Branding i nazwa projektu

- Zmienić nazwę `fastapi-full-stack-template` w `package.json` oraz `package-lock.json`.
- Zaktualizować tytuł strony w `frontend/index.html` z `Full Stack FastAPI Project` na nazwę aplikacji.
- Usunąć referencję do `/vite.svg` w `frontend/index.html`, jeśli plik nie jest używany.
- Zastąpić logo FastAPI własnym brandingiem w `frontend/src/components/Common/Logo.tsx`.
- Zaktualizować stopkę w `frontend/src/components/Common/Footer.tsx`:
  - tekst `Full Stack FastAPI Template`,
  - link do repozytorium FastAPI,
  - linki do profili FastAPI na X i LinkedIn.

### Konfiguracja GitHub

- Usunąć albo skonfigurować `.github/workflows/add-to-project.yml`, ponieważ obecnie wskazuje na projekt organizacji `fastapi`.
- Zaktualizować `.github/ISSUE_TEMPLATE/config.yml`:
  - kontakt bezpieczeństwa `security@tiangolo.com`,
  - linki do Discussions repozytorium FastAPI.
- Usunąć lub przepisać `.github/ISSUE_TEMPLATE/privileged.yml`, ponieważ odnosi się do użytkownika `@tiangolo`.
- Ustalić główny branch (`main`, `master` albo `dev`) i dopasować do niego workflowy:
  - `.github/workflows/test-backend.yml`,
  - `.github/workflows/playwright.yml`.

### Dokumentacja

- [x] Zaktualizować główny `README.md`, ponieważ opisuje część funkcji jako przyszłe, mimo że categories, obligations i ledger sharing już istnieją.
- [x] Ograniczyć w `frontend/README.md` ogólne instrukcje odziedziczone po template.
- [x] Usunąć odniesienia do `localhost.tiangolo.com` z `development.md`.
- [x] Ujednolicić workflow frontendowy na Bun.

## Zalecane pliki repozytorium

- `LICENSE`
- `SECURITY.md`
- `CONTRIBUTING.md`
- aktualne formularze issue dla bugów i feature requestów

## Stan Git

- Repozytorium nie ma jeszcze skonfigurowanego remote GitHub.
- Aktualny lokalny branch to `dev`.

## Plan etapami

### Obecny sprint — przed publikacją

- branding i nazwa projektu,
- GitHub workflows i issue templates,
- README oraz podstawowe pliki repozytorium.

### Kolejny etap

- dalsze porządki w dokumentacji developerskiej,
- ujednolicenie package managera,
- przegląd linków i ustawień projektu.

### Sprint za około 3 sprinty

- pełne uporządkowanie konfiguracji Docker/Compose,
- domeny lokalne i produkcyjne,
- deployment,
- konfiguracja sekretów i środowisk CI/CD.
