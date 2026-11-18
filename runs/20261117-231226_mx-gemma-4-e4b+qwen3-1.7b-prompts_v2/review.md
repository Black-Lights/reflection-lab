# Review sheet · 20261117-231226_mx-gemma-4-e4b+qwen3-1.7b-prompts_v2

Flagged by the rules; check and put corrections in review_overrides.json.

## n04 · baseline → c (expected content unsupported ['10:15'])

Q: At what time do doors open for the Sunday matinee?

Ref: 10:15 (45 minutes before 11:00).

> The Sunday matinee starts at 11:00, and doors open 45 minutes before each concert. Therefore, doors open at 10:15.

## fn04 · baseline → h (wrong value: unsupported [59.0, 14.0, '6:15', '6:30', '6:45', '7:00', '7:15', '7:30', '7:45', '8:00', '8:15', '8:30', '8:45'])

Q: How many buses leave Central Station between 06:00 and 08:59 on a weekday?

Ref: 12 (every 15 minutes: 06:00, 06:15, ..., 08:45).

> On weekdays, buses leave Central Station every 15 minutes from 06:00 to 09:00. The time period from 06:00 to 08:59 covers 3 hours and 59 minutes. The number of 15-minute intervals in this period is calculated as follows:
> 
> From 06:00 to 07:00: 5 buses (06:00, 06:15, 06:30, 06:45, 07:00)
> From 07:00 to 08:00: 5 buses (07:00, 07:15, 07:30, 07:45, 08:00)
> From 08:00 to 08:59: 4 buses (08:00, 08:15, 08:30, 08:45)
> 
> Total buses: 5 + 5 + 4 = 14.

## fm01 · baseline → h (wrong value: unsupported [4.4])

Q: A 5-year-old and a 9-year-old ride with one adult who has a RideCard. What do the three pay together for one single trip each?

Ref: 5.00 euros: adult 2.20 (RideCard), 9-year-old 2.80 (single ticket), 5-year-old free.

> The 5-year-old travels free. The 9-year-old pays 2.20 euros with the RideCard. The adult pays 2.20 euros with the RideCard. Therefore, the three pay a total of 4.40 euros for one single trip each.
