seperate ar weave into 2 posts , user informaion and auction information the user will pay seperalty 
.05 to creat account and then .05 to post items to the server for auction this will display in a diolog box
on fist auction posting or on fist log out. 

after dowload the application should activly background process this data for auctions 
and cross reference the nano wallet-item relationship to update the ar weave logs this will
tell the application who won the auction and cound the verifications of the win for 24 hours or 
after a limit.


all arweave posts will have the current auction data that the application has available 
if an auction ends all users will decide the final results. only the infotmaion for expired auction
and close to ending auctions.
item name, current winner, sale price, end time, current time, active or expired

every time a user make an ar post the the item win will have and auction win comfiormation

the applicaion will load expored auction for the last day to authenticat the wins 



NEW ITEM CREATION 
user account is nano index 0 they generate wallets under their seed with inxes 1 and 2 ect

Component	Strategy
User Seed	Stored securely by user (or encrypted in local storage)
Item Wallet Index	Incremental or UUID-based index per item
Public Key	Stored on Arweave for each item
Private Key	Derived on demand from seed + index (never stored)
Recovery	User can regenerate all item wallets from seed
To avoid collisions or reuse:
derive index from a hash of item ID (e.g. index = hash(item_id) % 2^32). sha 256
To avoid reoccurrence (i.e. duplicate indexes), use:
python
import hashlib

def generate_index(item_id: str) -> int:
    hash_bytes = hashlib.sha256(item_id.encode()).digest()
    return int.from_bytes(hash_bytes[:4], 'big')  # 32-bit index
This gives you a deterministic, unique index for each item based on its ID, with extremely low collision probability.

create account -> generate nano wallet index 0 -> create item -> generate item wallet index 1 -> send item ID
to this nano wallet as first transaction -> post item inf and wallet public key to arweave json for upoad 