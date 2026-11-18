# Leboncoin MCP

Read-only access to Leboncoin classified ads, so an assistant can find items to buy and assess their sellers.

## Ads

**Ad**:
An item offered for sale on Leboncoin. Requests to buy are outside this domain.
_Avoid_: Listing, annonce, offer, demand

**Ad summary**:
The short form of an Ad shown in search results: enough to decide whether the full Ad is worth reading.
_Avoid_: Preview, snippet, card

**Category**:
The section of Leboncoin an Ad is published in.
_Avoid_: Section, type

**Category attributes**:
The facts that only make sense within one Category, such as a car's mileage or a bike's frame size.
_Avoid_: Specs, properties, criteria

**Unpriced ad**:
An Ad published without a price. Not the same as an Ad priced at zero.
_Avoid_: Free ad

**Shippable ad**:
An Ad whose item can be delivered, so its distance to the buyer does not matter.
_Avoid_: Deliverable, livraison

**Unavailable ad**:
An Ad buyers can no longer reach, whatever the reason.
_Avoid_: Deleted ad, missing ad

## Sellers

**Seller**:
The person or shop that published an Ad.
_Avoid_: Owner, user, store, vendeur

**Private seller**:
A Seller acting as an individual.
_Avoid_: Particulier, individual

**Pro seller**:
A Seller acting as a business.
_Avoid_: Professional, shop, store

**Rating**:
A Seller's average review score, with the number of reviews behind it.
_Avoid_: Feedback, score, note

## Places

**Region**:
A current French administrative region, such as Nouvelle-Aquitaine.
_Avoid_: Leboncoin region

**Department**:
A French administrative department, such as Gironde.
_Avoid_: Département, county

**City**:
A French municipality, named as a person would name it, optionally with its postcode to tell homonyms apart.
_Avoid_: Town, commune, location

**Radius**:
The distance in kilometres around a City within which Ads are searched.
_Avoid_: Range, distance

## Searching

**Search URL**:
The address of a search made on the Leboncoin site or app, carrying all its filters, including those this server does not expose.
_Avoid_: Saved search, search link

**Page**:
One fixed-size slice of a search's Ads, in the order the search sorts them.
_Avoid_: Batch, chunk, offset

**Total**:
How many Ads match a search, whatever number of Ad summaries is returned.
_Avoid_: Count, hits

## Access

**Blocked**:
Leboncoin refused to answer this server, regardless of what was asked. Says nothing about the Ad or Seller requested.
_Avoid_: Unavailable, banned, rate-limited
