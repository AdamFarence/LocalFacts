# LocalLens
Bringing the locals together — Representatives, Data, People

# Table of Contents:
### TKTK

# General setup (thus far):
- Entering an address returns a lat/lon pair, which is then used to find federal elected officials (state is in the works). That data includes office locations, contact info, and links to pictures, among other things. That data is then used to query bulk Legiscan data and return voting history. It's a mess at the moment; only the raw JSON data is printed.

# Adam's next steps:
- Find additional data that can get pulled in and localized. Also try to find historical data so trends can be shown.

# Notes:
- Having trouble getting the Legiscan API to work for individuals. Might be easier to download legislative data in bulk, store it locally, and have the application check that JSON data for updates. Would have to set an update schedule, though.

## Potential Datasets
Legiscan Bulk Datasets

## Potential APIs
Google Air quality API: https://developers.google.com/maps/documentation/air-quality/overview

Google Pollen API: https://developers.google.com/maps/documentation/pollen?hl=en&_gl=1*1360p25*_ga*MTQxMzg2NDc5NC4xNzQwMTE3Mjky*_ga_NRWSTWS78N*MTc0MDE3NjQ1Ny4xLjEuMTc0MDE3NjQ4My4wLjAuMA..

