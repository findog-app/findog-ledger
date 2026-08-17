# Roadmapa deploymentu na VPS

Plan dotyczy wdrożenia Findog Ledger na obecnym VPS-ie. Dokument opisuje docelową architekturę i kolejność prac; sam w sobie nie zmienia konfiguracji aplikacji ani serwera.

## Stan obecny VPS-a

- Docker i Docker Compose są zainstalowane.
- Działają dwa stacki Compose: `firefly` i `ff-toolkit`.
- Publiczne porty `80` i `443` obsługuje kontener Nginx `ff-iii-edge-proxy` ze stacku `ff-toolkit`.
- Nginx i aplikacje Firefly komunikują się przez zewnętrzną sieć Docker `firefly_net`.
- Certyfikaty TLS są obsługiwane przez Certbota z weryfikacją DNS Cloudflare.
- Strefa DNS ma wildcard `*.m.wilczur.cc`, więc nowe subdomeny nie wymagają osobnych rekordów DNS, o ile wildcard nadal wskazuje na VPS.

Wniosek: nie należy uruchamiać projektowego Traefika z `compose.traefik.yml`, ponieważ kolidowałby z istniejącym Nginx na portach 80/443. Findog Ledger powinien zostać dodany jako kolejny stack za tym Nginx-em.

## Docelowa architektura

Przykładowe nazwy hostów:

```text
ledger.m.wilczur.cc      -> frontend:80
api.ledger.m.wilczur.cc  -> backend:8000
                             -> PostgreSQL (wyłącznie wewnętrznie)
```

Docelowy przepływ wydania:

```text
push / tag Git
      -> GitHub Actions: testy i budowa obrazów
      -> GHCR: backend i frontend oznaczone wersją
      -> VPS: docker compose pull + up --no-build
      -> Nginx: ruch HTTPS do odpowiednich kontenerów
```

## Etap 1: przygotowanie repozytorium

1. Dodać workflow GitHub Actions, który uruchamia testy, buduje obrazy i publikuje je do GHCR:
   - `ghcr.io/wini83/findog-ledger-backend`;
   - `ghcr.io/wini83/findog-ledger-frontend`.
2. Publikować obrazy pod niezmiennymi tagami (`v0.1.0`, SHA commita); `latest` może być wyłącznie tagiem pomocniczym.
3. Dodać `compose.production.yml`:
   - używa gotowych obrazów z GHCR i zmiennej `TAG`;
   - nie buduje obrazów na VPS-ie;
   - dołącza frontend i backend do zewnętrznej sieci `firefly_net`;
   - nie wystawia portów aplikacji ani PostgreSQL na hosta;
   - udostępnia Adminer wyłącznie przez HTTPS i HTTP Basic Auth, gdy jest wyraźnie potrzebny;
   - nie uruchamia PostgreSQL ani wolumenu danych, ponieważ produkcja korzysta z zewnętrznie zarządzanej bazy.
4. Dodać `.env.production.example`, bez wartości sekretów, z pełną listą wymaganych zmiennych, m.in. `TAG`, `DOMAIN`, `FRONTEND_HOST`, `BACKEND_CORS_ORIGINS`, dane PostgreSQL, `SECRET_KEY`, konto administratora i SMTP.
5. Upewnić się, że frontend odczytuje produkcyjne `VITE_API_URL` w chwili startu kontenera, np. `https://api.ledger.m.wilczur.cc`. Wartość jest generowana do niecache'owanego `config.js`, dzięki czemu ten sam obraz może działać na różnych środowiskach.

## Etap 2: jednorazowe przygotowanie VPS-a

1. Utworzyć katalog aplikacji, np. `/home/wini/findog-ledger`.
2. Umieścić w nim `compose.production.yml` oraz produkcyjny `.env`, utworzony na podstawie `.env.production.example`. Sekretów nie zapisujemy w repozytorium ani obrazach.
4. Dopisać do `/home/wini/ff-toolkit/nginx-edge.conf` dwa bloki virtual hostów:
   - `ledger.m.wilczur.cc` kierujący do usługi frontendowej na porcie `80`;
   - `api.ledger.m.wilczur.cc` kierujący do usługi backendowej na porcie `8000`.
5. Wydać lub rozszerzyć certyfikat TLS przez obecny mechanizm Certbot/Cloudflare. Wildcard `*.m.wilczur.cc` nie obejmuje `api.ledger.m.wilczur.cc`, więc tę nazwę trzeba dopisać do certyfikatu jawnie.
6. Przeładować istniejący Nginx i sprawdzić dostępność obu hostów po HTTPS.

## Etap 3: pierwszy deploy

Na VPS-ie, z katalogu aplikacji:

```bash
docker compose -f compose.production.yml pull
docker compose -f compose.production.yml up -d --no-build
```

Usługa `prestart` powinna potwierdzić połączenie z zewnętrznym PostgreSQL i uruchomić migracje Alembica przed startem backendu.

Po uruchomieniu należy sprawdzić:

- `docker compose ps` oraz logi backendu i `prestart`;
- odpowiedź endpointu health check;
- logowanie i komunikację frontendu z API;
- certyfikat oraz przekierowanie HTTP do HTTPS.

## Kolejne wydania i rollback

Kolejny deploy polega na użyciu nowego, konkretnego tagu:

```bash
TAG=v0.2.0 docker compose -f compose.production.yml pull
TAG=v0.2.0 docker compose -f compose.production.yml up -d --no-build
```

Rollback obrazu przebiega tak samo, z poprzednim tagiem. Należy jednak projektować migracje bazy jako kompatybilne wstecz albo mieć osobny, świadomy plan cofania migracji — cofnięcie samego obrazu nie cofa struktury bazy danych.

## Decyzje przed implementacją

- Potwierdzić nazwy hostów (proponowane: `ledger.m.wilczur.cc` i `api.ledger.m.wilczur.cc`).
- Zdecydować, czy pakiety GHCR będą publiczne, czy prywatne.
- Ustalić, czy deploy ma być ręczny przez SSH, czy wywoływany z GitHub Actions po wydaniu release.
- Ustalić politykę backupów zewnętrznej bazy PostgreSQL przed pierwszym użyciem produkcyjnym.
