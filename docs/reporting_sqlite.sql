-- SQLite-compatible version of docs/reporting.sql
-- Count of trips whose Pickup -> Dropoff duration exceeded 1 hour,
-- grouped by month and driver.

WITH pickup_events AS (
    SELECT
        id_ride_id AS id_ride,
        created_at AS pickup_at
    FROM ride_event
    WHERE description = 'Status changed to pickup'
),
dropoff_events AS (
    SELECT
        id_ride_id AS id_ride,
        created_at AS dropoff_at
    FROM ride_event
    WHERE description = 'Status changed to dropoff'
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
    strftime('%Y-%m', td.pickup_at)                      AS month,
    u.first_name || ' ' || substr(u.last_name, 1, 1)      AS driver,
    COUNT(*)                                               AS count_of_trips_gt_1hr
FROM trip_durations td
JOIN "user" u ON u.id = td.id_driver
WHERE td.duration_hours > 1
GROUP BY month, driver
ORDER BY month, driver;