from dotenv import load_dotenv
load_dotenv()

from backend.database import DatabaseManager
import asyncio

async def get_creds():
    db = DatabaseManager()
    await db.connect()
    accs = await db.get_all_accounts()
    if accs:
        a = accs[0]
        print(f'TL_EMAIL={a.tl_email}')
        print(f'TL_PASSWORD={a.tl_password}')
        print(f'TL_ACCOUNT_ID={a.tl_account_id}')
        print(f'TL_PROP_FIRM={a.tl_prop_firm}')
    await db.disconnect()

asyncio.run(get_creds())
