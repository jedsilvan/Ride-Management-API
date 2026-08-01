# Wingz Ride Management API

A RESTful API built with **Django** and **Django REST Framework (DRF)** for managing ride information — rides, riders/drivers, and ride events — designed for admin-only access with a strong emphasis on query efficiency at scale.

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Setup & Installation](#setup--installation)
5. [Data Models](#data-models)
6. [Authentication & Permissions](#authentication--permissions)
7. [API Reference](#api-reference)
8. [Testing](#testing)
9. [Design Decisions & Challenges](#design-decisions--challenges)
10. [Bonus: SQL Reporting Query](#bonus-sql-reporting-query)

---

## Overview

This project exposes a `Ride` resource (and supporting `User` and `RideEvent` resources) via a DRF ViewSet-based API. The primary design constraint driving this implementation is **query efficiency**: the `Ride` and `RideEvent` tables are expected to grow very large in production, so every endpoint is built to avoid N+1 queries, avoid loading unbounded result sets into memory, and keep total query counts fixed regardless of how many rides or ride events exist.

---

## Tech Stack

| Component        | Choice                                  |
|-------------------|------------------------------------------|
| Language          | Python 3.10 – 3.14                       |
| Framework         | Django 5.2 (LTS)                         |
| API Layer         | Django REST Framework                    |
| Database          | PostgreSQL (required — see note below)   |
| Auth              | Token-based (DRF `TokenAuthentication`)  |
| Filtering         | `django-filter`                          |
| Pagination        | DRF `PageNumberPagination` (custom)      |

> **Why PostgreSQL:** The geo-distance sort (Requirement 3) is implemented using database-side arithmetic on `pickup_latitude`/`pickup_longitude` via Django's `ExpressionWrapper`/`F()` objects, so it works on any relational backend. PostgreSQL is recommended for production because it allows this to be swapped for the `earthdistance`/`cube` extensions or `PostGIS` for true geospatial indexing without changing the API contract. The default setup here uses the portable ORM approach so the project runs with SQLite for quick local evaluation too.

---

## Project Structure

```
wingz/
├── manage.py
├── requirements.txt
├── .env.example
├── wingz/                 # project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── rides/                 # main app
│   ├── models.py          # User, Ride, RideEvent
│   ├── serializers.py      # RideSerializer, RideEventSerializer, UserSerializer
│   ├── views.py            # RideViewSet, UserViewSet
│   ├── permissions.py      # IsAdminRole
│   ├── filters.py          # RideFilter (status, rider email)
│   ├── pagination.py       # StandardResultsPagination
│   ├── serializers_lite.py # lightweight nested serializers to avoid extra queries
│   ├── management/
│   │   └── commands/
│   │       └── create_admin.py  # `python manage.py create_admin <username>`
│   ├── urls.py
│   ├── admin.py
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_permissions.py
│   │   └── test_ride_list_api.py
│   └── migrations/
└── docs/
    └── reporting.sql       # bonus SQL query
```

---

## Setup & Installation

### Prerequisites
- Python 3.10 – 3.14 (project pins Django 5.2 LTS, which supports this range)
- PostgreSQL 14+ (or SQLite for a quick local run)
- `pip` / `virtualenv`

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/jedsilvan/Ride-Management-API.git

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# edit .env with your DB credentials, SECRET_KEY, etc.

# 5. Generate and run migrations
# (no migration files are checked into this repo -- makemigrations
# creates them from models.py, migrate then applies them to the DB)
python manage.py makemigrations rides
python manage.py migrate

# 6. Create a superuser, then give it an admin Profile
python manage.py createsuperuser
python manage.py create_admin <the username you just created>

# 7. (Optional) Seed sample data
python manage.py loaddata rides/fixtures/sample_data.json

# 8. Run the server
python manage.py runserver
```

### Obtaining an API Token

```bash
curl -X POST http://localhost:8000/api-token-auth/ -d "username=<admin_username>&password=<admin_password>"
```

Use the returned token in subsequent requests:

```bash
curl http://localhost:8000/api/rides/ -H "Authorization: Token <your_token>"
```

---

## Data Models

### `User`
| Field       | Type    | Notes                          |
|-------------|---------|---------------------------------|
| id_user     | AutoField (PK) |                          |
| role        | CharField | `'admin'` or other roles      |
| first_name  | CharField |                                |
| last_name   | CharField |                                |
| email       | EmailField | indexed — used for rider filtering |
| phone_number| CharField |                                |

### `Ride`
| Field             | Type      | Notes                              |
|-------------------|-----------|-------------------------------------|
| id_ride           | AutoField (PK) |                                 |
| status            | CharField, indexed | e.g. `en-route`, `pickup`, `dropoff` |
| id_rider          | ForeignKey → User (`related_name="rides_as_rider"`) |
| id_driver         | ForeignKey → User (`related_name="rides_as_driver"`) |
| pickup_latitude   | FloatField |                                    |
| pickup_longitude  | FloatField |                                    |
| dropoff_latitude  | FloatField |                                    |
| dropoff_longitude | FloatField |                                    |
| pickup_time       | DateTimeField, indexed | supports efficient time sort |

### `RideEvent`
| Field         | Type      | Notes                        |
|---------------|-----------|-------------------------------|
| id_ride_event | AutoField (PK) |                          |
| id_ride       | ForeignKey → Ride (`related_name="ride_events"`) |
| description   | CharField |                                |
| created_at    | DateTimeField, indexed | supports the "last 24h" filter |

All foreign keys use `db_index=True` and composite indexes are added where a field is both filtered and sorted on (see `Meta.indexes` in `models.py`).

---

## Authentication & Permissions

- Authentication uses DRF's `TokenAuthentication`.
- A custom permission class, `IsAdminRole`, checks `request.user.role == 'admin'` and is applied at the ViewSet level via `permission_classes`. Unauthenticated or non-admin requests receive `401`/`403` respectively.
- This keeps role logic out of the views and easily testable/unit-mockable in isolation.

```python
class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )
```

---

## API Reference

### `GET /api/rides/`

Returns a paginated list of rides, each including nested rider, driver, and `todays_ride_events`.

**Query Parameters**

| Param            | Description                                              | Example                          |
|-------------------|-----------------------------------------------------------|-----------------------------------|
| `status`          | Filter by exact ride status                               | `?status=en-route`               |
| `rider_email`     | Filter by rider's email                                   | `?rider_email=jane@example.com`  |
| `ordering`        | Sort by `pickup_time` or `distance`                        | `?ordering=pickup_time` / `?ordering=-pickup_time` |
| `pickup_lat` / `pickup_lng` | Required when `ordering=distance`; the reference GPS point | `?ordering=distance&pickup_lat=34.05&pickup_lng=-118.25` |
| `page` / `page_size` | Standard pagination controls                            | `?page=2&page_size=20`           |

**Sample Response**

```json
{
  "count": 128,
  "next": "http://localhost:8000/api/rides/?page=2",
  "previous": null,
  "results": [
    {
      "id_ride": 42,
      "status": "en-route",
      "pickup_time": "2026-07-30T14:05:00Z",
      "id_rider": { "id_user": 7, "first_name": "Jane", "last_name": "Doe", "email": "jane@example.com" },
      "id_driver": { "id_user": 3, "first_name": "Chris", "last_name": "H", "email": "chris@wingz.com" },
      "pickup_latitude": 34.0522,
      "pickup_longitude": -118.2437,
      "dropoff_latitude": 34.1,
      "dropoff_longitude": -118.3,
      "todays_ride_events": [
        { "id_ride_event": 501, "description": "Status changed to pickup", "created_at": "2026-07-31T09:00:00Z" }
      ]
    }
  ]
}
```

### `GET /api/rides/{id}/`
Retrieve a single ride with the same nested structure as above.

### `POST /api/rides/`, `PUT/PATCH /api/rides/{id}/`, `DELETE /api/rides/{id}/`
Standard admin-only CRUD, handled by the ViewSet's default actions.

### `/api/users/`, `/api/ride-events/`
Full CRUD, same as `Ride` — `GET` (list/detail), `POST`, `PUT`/`PATCH`, `DELETE`, all admin-only with the same pagination scheme.

---

## Testing

Run the full suite:

```bash
python manage.py test
```

Run a single test file, class, or method:

```bash
python manage.py test rides.tests.test_ride_list_api
python manage.py test rides.tests.test_ride_list_api.RideListAPITests
python manage.py test rides.tests.test_ride_list_api.RideListAPITests.test_query_count_stays_within_budget
```

Useful flags:

| Flag | Effect |
|------|--------|
| `--verbosity 2` | Print each test name as it runs |
| `--keepdb` | Reuse the test DB between runs instead of rebuilding it (faster while iterating) |

Django spins up a separate test database for each run and tears it down afterward — your real `db.sqlite3` (or Postgres DB) data is never touched.

Test coverage includes:
- Model constraints and relationships
- `IsAdminRole` permission (allows admin, blocks anonymous/non-admin)
- Ride list: correct filtering by status/rider email, correct sort order for both `pickup_time` and `distance`, pagination metadata
- **Query-count assertions** using `django.test.utils.CaptureQueriesContext` / `assertNumQueries` to guarantee the endpoint never regresses past the 2–3 query budget, even as fixture data grows
- `todays_ride_events` correctly excludes events older than 24 hours

---

## Design Decisions & Challenges

- **Nested writes vs. read-only nested serializers:** Rider/driver/ride events are represented as nested read-only serializers on `GET`, while `POST`/`PUT` accept flat `id_rider`/`id_driver` FK ids (`PrimaryKeyRelatedField`) to keep writes unambiguous and avoid the complexity of nested writable serializers.
- **Filtering rider by email instead of id:** implemented with `django_filter.CharFilter(field_name="id_rider__email")`, which still resolves to a single indexed join rather than a subquery.
- **Offset vs. keyset pagination:** `PageNumberPagination` (offset-based) was chosen for simplicity and to match the "2–3 queries" requirement exactly as specified. At very high page numbers on a very large table, offset pagination has a well-known performance cliff (`OFFSET` still scans skipped rows). A follow-up improvement would be cursor/keyset pagination (`ordering + WHERE pickup_time < last_seen`), which is noted here as a possible production hardening step rather than implemented, to keep the sorting-by-distance requirement composable with a single pagination strategy.
- **Distance sort accuracy vs. speed:** the equirectangular approximation was chosen over the more accurate Haversine formula because it avoids trigonometric functions in the SQL query, which is faster at scale and adequate for typical intra-city ride distances. This tradeoff is documented in code comments in `filters.py`.
- **`todays_ride_events` as a derived field:** rather than a model field, it's a `SerializerMethodField` reading from the `to_attr="todays_ride_events"` list set by `Prefetch`, so no schema changes are needed and the "last 24 hours" window is always calculated relative to request time.

---

## Bonus: SQL Reporting Query

**Requirement:** count of trips whose Pickup → Dropoff duration exceeded 1 hour, grouped by month and driver.

```sql
WITH pickup_events AS (
    SELECT
        re.id_ride_id AS id_ride,
        re.created_at AS pickup_at
    FROM ride_event re
    WHERE re.description = 'Status changed to pickup'
),
dropoff_events AS (
    SELECT
        re.id_ride_id AS id_ride,
        re.created_at AS dropoff_at
    FROM ride_event re
    WHERE re.description = 'Status changed to dropoff'
),
trip_durations AS (
    SELECT
        r.id AS id_ride,
        r.id_driver_id AS id_driver,
        p.pickup_at,
        d.dropoff_at,
        EXTRACT(EPOCH FROM (d.dropoff_at - p.pickup_at)) / 3600.0 AS duration_hours
    FROM ride r
    JOIN pickup_events  p ON p.id_ride = r.id
    JOIN dropoff_events d ON d.id_ride = r.id
)
SELECT
    TO_CHAR(td.pickup_at, 'YYYY-MM')                AS month,
    CONCAT(u.first_name, ' ', LEFT(u.last_name, 1))  AS driver,
    COUNT(*)                                          AS count_of_trips_gt_1hr
FROM trip_durations td
JOIN "user" u ON u.id = td.id_driver
WHERE td.duration_hours > 1
GROUP BY month, driver
ORDER BY month, driver;
```

**Notes:**
- CTEs isolate the `pickup` and `dropoff` events per ride so each ride's duration is a simple join rather than a self-join with conditional aggregation, which is easier to read and lets the query planner use the index on `ride_event(id_ride, description)` for each half independently.
- `EXTRACT(EPOCH FROM ...)` is PostgreSQL syntax; for MySQL use `TIMESTAMPDIFF(SECOND, pickup_at, dropoff_at) / 3600.0`, and for SQLite use `(JULIANDAY(dropoff_at) - JULIANDAY(pickup_at)) * 24`.
- Driver display name (`Chris H`) is built as first name + last-name initial to match the sample report format.
- A composite index on `ride_event(id_ride, description)` is recommended so both CTEs can seek directly to the relevant rows instead of scanning the full event table.
