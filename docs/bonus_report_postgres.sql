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