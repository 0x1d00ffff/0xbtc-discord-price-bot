# Tipbot notes

Bot has a single priv/pubkey, all balances are in one account and bookkeeping is done in a db. Deposits are initiated through a bot command which generates a URL to a dapp (containing a unique ID). The dapp shows a deposit interface and attaches the ID to all deposits. 

Allow binding eth address to discord user?
PROS:
  - allows tipping to nametagtoken with no fees (goes to user's balance)
  - allows cool commands like !nametagsof @<discord_sn>
 
CONS:
  - requires on-chain tx (with eth) to prove ownership
  - more contract complexity (add function to actually verify address)
  - slightly more complex bot logic

Commands: 
`!deposit`
  generates url depositdapp.com?id=XX. deposit contract emits event on deposit containing ID
`!tip @<discord_sn> <amount>`
`!tip <ethaddress|nametagtoken> <amount>`
  asks for confirm (or allows cancel) since it costs lava
`!withdraw <amount>` 
  asks for confirm (or allows cancel) since it costs lava, <amount> optional
`!withdrawto <ethaddress|nametagtoken> <amount>`
  functionally same as tip, maybe <amount> is optional
`!rain <amount>`
  divide up <amount> lava among active users (?) and tip them all
`!register`
  If we allow tipping to nametagtokens w/o fees, this generates a url to the dapp which uses on-chain tx to verify address ie depositdapp.com?register&id=XX
`!register  <eth_address|nametagtoken>`
 Alternate version of above if nametagtokens are simply treated as external accounts.

Deposit dapp:
 - requires ID in url to work (each !deposit or !register generates unique ID)
 - allow lava deposits
 - allow NTT binding


Deposit contract:
 - `deposit_to_balance(amount, id)` that allows people to deposit lava into the bot
 - `register_eth_address(id)` that allows binding an eth address to a discord username


Remaining questions
 - what to do if user loses discord tag?
 - How to prevent random user from thinking he can use someone else's deposit link? Then he will lose all that money
    - Could add discord username to url so page could say DEPOSITING FOR USER123. Would have to base64 it or something since discord allows unicode.
    - Could make !register and !deposit PM-only

