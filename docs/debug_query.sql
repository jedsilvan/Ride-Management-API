WITH pickup_events AS (
    SELECT id_ride_id AS id_ride, created_at AS pickup_at
    FROM ride_event WHERE description = 'Status changed to pickup'
),
dropoff_events AS (
    SELECT id_ride_id AS id_ride, created_at AS dropoff_at
    FROM ride_event WHERE description = 'Status changed to dropoff'
),
trip_durations AS (
    SELECT
        r.id AS id_ride,
        r.id_driver_id AS id_driver,
        p.pickup_at,
        d.dropoff_at,
        (JULIANDAY(d.dropoff_at) - JULIANDAY(p.pickup_at)) * 24.0 AS duration_hours
    FROM ride r
    JOIN pickup_events  p ON p.id_ride = r.id
    JOIN dropoff_events d ON d.id_ride = r.id
)
SELECT
    td.id_ride,
    td.id_driver,
    u.first_name,
    u.last_name,
    td.pickup_at,
    td.dropoff_at,
    td.duration_hours,
    CASE WHEN td.duration_hours > 1 THEN 'YES' ELSE 'no' END AS over_1hr
FROM trip_durations td
LEFT JOIN "user" u ON u.id = td.id_driver;