# CLI bonds monitor tool

## General description
I want to create a CLI tool for monitoring current market situation for bonds.
The key information pieces about this project:
- This is 100% python project
- I have a QUIK terminal. There is python lib that gives python access to QUIK terminal. The current market data will be coming from this source.
- This is the 1st stage of this project, there might be more to follow. The 1st stage is about monitoring hard-ccy bonds
- There are hard ccy bonds traded on MOEX exchange - in USD, EUR and CNH mostly. 
  - For some CHN bonds there are CNH orderbooks.
  - But most of trading happens in RUB orderbooks (especially since there is no real USD and EUR in MOEX)
- The trading mechanics is this - bonds are quoted in % of par (as everywhere), trades settle in RUB @ CBR fx rate fixed for the trade date.
  - Economically CBR fx rate for today is determined the day before, so it's some yesterday's rate
  - Because of this, since trades are settled not at market rate, but at some fixed rate, the % prices should (and do) change as market fx quote changes.
  - If market fx goes higher than CBR rate, the % price should go higher (as you are paying less rub than should have, meaning effective % price is lower). And vice a versa.
- The CLI app should be showing some kind of table for bonds, updating the prices periodically and doing the necessary calculations.

## More specific tech task
---
### Market data input
---
#### Market data from QUIK
- The market data input comes from a QUIK table with "current trading".
- The list of bonds is setup at the QUIK level (each bond might have more than one trading mode - e.g. CNY, RUB etc)
- We setup a correspondence table that shows which column of the QUIK table corresponds to which field we track
- QUIK market data tables have different rows for different trading boards. For instance, orderbooks in RUB and CNH will have different trading boards code
  - Another trading board type is negotiated deals - done directly between 2 counterparties. These entries will contain valuable volumes / trade numbers data
  - Another trading board type is repo - so it's possible to see avg repo rate and total size of repo deals for a given ISIN

#### Other sources of market data
- There's also other type of market data - fx rates - that will be coming from inhouse system.
- The program should leave some interface for which i will use my hand-written module to provide this market data
- Current market fx rates come from this market data source
- CBR FX rates are also coming from that market data source 

#### Pre-filtering
The input list of bonds is coming from the QUIK table. It should be possible to set primary filter based on certain rules. 
For example, it should be possible to filter out all the bonds with outstanding notionals less than X.
(Technically we will be adding all the coproate bonds into the QUIK table, then the program should filter all the bonds with notional other than RUB. 
But this list will contain a lot of "junk" - small issues, scturctured credit issues etc. To avoid filtering manually there should be a way to set up first stage filter)

### Calculations
---
There's a number of calculations to be carried out by the program
#### RUB->HCY orderbook prices conversion
Observable RUB prices should be convertible to real HCY prices (which then will be used to calculate parameters like yield).
The conversion logic is this:
$PX_{hcy} + AI = (PX_{rub}+AI) * FX_{cbr} / FX_{market}$

#### In house lib
We utilize inhouse lib to calculate different financial parameters (like bonds yields, duration, z-sreads etc).
This data will be calculated using the lib.

##### Lib interface setup 
You should provide for an interface for which I will implement an adapter to use my inhouse lib.

#### Which static data comes from where
Some static data lives in the inhouse lib (I can pull bonds definition using ISIN).
For some bonds I don't have a static data. Also, i'll use accrued interest calculated by the exchange in the formula - I should be able to pull it from there

#### Extra data in columns
It should be possible to add some extra columns data that aggregates some valuable input.
For instance:
- Total trading volume in the bond (for different trading boards)
- Avg repo rate for the bond

### Interface
---
#### Navigation
Since it's a CLI, there should be convenient navigation keyboard interface
I want vim-motions (like going up-down with k-j, Ctrl-u, Ctrl-d). I also want ability to select and copy certain lines / columns (probably implemented with something like "v")
- Please also implement quick find / jumps (probably with "/" and "?" like in vim) to find and go to certain issues

#### Interface config
Interface config should be settable in a special config file. That means - setting columns.
Normally columns will be: 
| Name | ISIN | CCY | Maturity/Put | Bid | Ask | Conv Bid | Conv Ask | Bid Yld | Ask Yld | Dur | TodVolume
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bnd | RU000...| USD | 09.2030 | 99.00 | 99.50 | 100.25 | 100.75 | 7.25% | 7.75% | 1.05| 257mm |

Here "Conv Bid" and "Conv Ask" are the converted prices from RUB prices. Yields are calculated from converted prices
TodVolume is trading volume for today across different trading 

#### Input/override
There should be a way to input / override prices. Bonds where the px is overriden should be marked somehow (so that it's easy to see, and reset it by pressing some shortcut)

#### Features
##### Sorting / filtering
It should be possible to filter / sort bonds easily with some keystrokes. For example, I might want to leave all the bonds with certain names (like "Minfin"), 
and/or leave only USD bonds, or both USD & EUR bonds, filter all bonds with maturity range of 2-3 years (that's term to maturity), or with duration < 0.5
**Please suggest what are the best options to implement this in terms of ease of use by a user**

##### Selection / copying
It should be able to select certain rows / columns and copy them to paste it somewhere else

##### Tabs feature
Please design the program in a way it's easy to add tabs (preset in config), between which it's easy to navigate. 

##### Popup feature
Please provide for functionality to open a CLI text hover popup upon pressing some button that might reveal extra info on the bond.

### Lags / recalculation / market data requests
There should be 2 recalculation modes - periodic (with period set in config), say once every 10 seconds, or manual, upon pressing some keys combination.
It should be possible to swithc between the 2 modes pressing a key
---

### Market data storage module
---
Please provide for ability to later implement some functionality that will store market data every X seconds in some database. This is not to be implemented now.
Just think about the way to do it properly.