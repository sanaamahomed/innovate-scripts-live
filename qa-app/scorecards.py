"""QA scorecards. Edit weights, wording or critical flags here; the app picks changes up on restart.

weight = points for the item. critical = a FAIL on this item fails the whole call.
"""

PASS_MARK = 85      # % at or above = Pass
COACH_MARK = 70     # % at or above (but below PASS_MARK) = Needs coaching

CARTRACK_FACTS = (
    'Product: Cartrack tracking, "Quick Gold with Cartrack Tag", R239 incl VAT per month, free installation, '
    "36 month contract, 10% escalation in year 2 and again in year 3, then CPI. Early cancellation: individuals "
    "R2,650 incl VAT or the balance of the contract (whichever is lesser); business clients the full balance. "
    "Admin fee R19. Payment by DebiCheck debit order (mandate sent to the client's banking app). The agent works "
    "for Innovate, a brokerage, on behalf of Cartrack/Motordrive SA. The verbal declaration has 7 points that the "
    "client must each answer with a clear YES: (1) debit order collection, (2) fees payable in advance plus "
    "pro-rata, (3) vehicle available for installation, (4) 24 hours notice or R600 call-out, (5) T&Cs on "
    "Cartrack's website, (6) installation proof shared with insurer, (7) verbal agreement accepted and binding. "
    "Agents must avoid slang, use the client's name more than 3 times, and verify in English then explain in the "
    "client's preferred language."
)

NETSTAR_FACTS = (
    "Product: Netstar vehicle tracking sold by Innovate (the brokerage, part of Cubix) on behalf of Netstar. "
    "Options: Early Warning at R239 per month, or Early Warning with StarTag back-up device at R259 per month "
    "(back-up battery lasts max 3 years and must be replaced). 36-month rental contract with free installation. "
    "Debit order normally on the client's salary date; first debit includes the month's premium plus a pro-rata "
    "amount for the rest of the month; client must confirm banking details are their own (otherwise written "
    "authority from the account holder) and authorise Netstar to debit monthly. Cancellation: 20 working days "
    "written notice plus a reasonable settlement fee. Full T&Cs are on the Netstar website and emailed; the call "
    "forms the basis of the contract. The call must state it is recorded. Close: ask whether installation is at "
    "home or work and get the street address (Google verify), confirm the device, and confirm the fitment date "
    "and time (Mon-Fri 8am-5pm, safe private area). An optional Repair Assist upsell may follow (Gold R149 per "
    "month, Motordrive SA debit). Marking guidance: judge each question as a whole (these are broad questions, "
    "not single phrases); BRAND is about professionalism and avoiding slang; OBJ is na if the client raised no "
    'objection; "Compliance critical" means a fail on the INTRO question is a critical failure.'
)


def _i(id, label, weight, group, critical=False, manual=False):
    return {"id": id, "label": label, "weight": weight, "group": group, "critical": critical, "manual": manual}


V, B = "Verification", "Behaviour"
CARTRACK = [
    _i("v_name", "Agent introduced themselves by name", 1, V),
    _i("v_broker", "Said they are calling from the brokerage (Innovate)", 1, V),
    _i("v_behalf", "Said they are calling on behalf of Cartrack", 1, V),
    _i("v_pkg", "Package confirmed (e.g. Quick Gold with Cartrack Tag)", 1, V),
    _i("v_ben", "3 benefits mentioned", 1, V),
    _i("v_work", "Vehicle in full working order, with a clear YES", 1, V),
    _i("v_price", "Correct price (R239 incl VAT)", 3, V, critical=True),
    _i("v_term", "Contract length (36 months)", 1, V),
    _i("v_incr", "Price increases explained (10% escalation, then CPI)", 1, V),
    _i("v_cancel", "Cancellation process and cost (R2,650 or balance of contract)", 3, V, critical=True),
    _i("v_debi", "DebiCheck explained", 1, V),
    _i("v_r19", "R19 fee explained", 1, V),
    _i("v_recap", "Customer details recapped (name, ID, contact, address, vehicle)", 1, V),
    _i("v_acct", "Business or personal account confirmed", 1, V),
    _i("v_vin", "VIN confirmed", 1, V),
    _i("v_decl", "Declaration read in full (all 7 points)", 3, V, critical=True),
    _i("v_yes", "Clear YES from the client for each declaration point", 3, V, critical=True),
    _i("v_pro", "Pro-rata explained (only if needed)", 1, V),
    _i("v_q", "Asked if the client has questions", 1, V),
    _i("b_tone", "Matched the client's tone and pace", 1, B, manual=True),
    _i("b_listen", "Active listening (acknowledged what the client said)", 1, B),
    _i("b_lang", "Verification in English, then explained in the client's preferred language", 1, B, manual=True),
    _i("b_name", "Used the client's name more than 3 times", 1, B),
    _i("b_slang", "Avoided slang", 1, B),
    _i("b_int", "Let the client ask questions without interrupting", 1, B, manual=True),
    _i("b_rep", "Repeated a clause if interrupted", 1, B, manual=True),
    _i("b_req", "Noted the client's specific requests", 1, B),
]

N = "Netstar scorecard"
NETSTAR = [
    _i("n_intro", "INTRO: Did the rep clearly identify themselves as calling on behalf of Netstar from Cubix?", 10, N, critical=True),
    _i("n_disc", "DISCLAIMER: Did the agent read the disclaimer verbatim or include all relevant disclosures (calls are recorded)?", 15, N),
    _i("n_pitch", "PITCH: Did the agent pitch the product correctly, allowing the client to make an informed decision?", 15, N),
    _i("n_prem", "PREM: Was the correct pro-rata and monthly premium given to the client?", 20, N),
    _i("n_kyc", "KYC: Client name, surname, ID number, contact numbers, postal address, including alternative numbers captured", 10, N),
    _i("n_bank", "BANK: Correct banking details captured and relevant information asked (salary/debit date; monetary obligations assumed by the client; manner of payment)", 20, N),
    _i("n_bankcl", "BANK: Were the banking clauses correctly done with the client?", 20, N),
    _i("n_veh", "KYC: Were the client's VEHICLE details captured correctly? (double or triple deal)", 20, N),
    _i("n_brand", "BRAND: Was the agent professional throughout the call?", 10, N),
    _i("n_obj", "OBJ: Did the agent attempt to objection handle, if applicable?", 10, N),
    _i("n_fais", "FAIS: Were the terms and conditions read verbatim or correctly? (including the rental clause)", 20, N),
    _i("n_inst", 'CLOSE: Did the agent ask "Where would you prefer to have installation done, at home or work?" and get a clear response (ask for address and Google verify)?', 15, N),
    _i("n_dev", "CLOSE: Did the agent capture the correct device for the client?", 20, N),
    _i("n_fit", "CLOSE: Was the fitment date and time confirmed by the agent with the client?", 15, N),
]

PRODUCTS = {
    "ct": {"name": "Cartrack", "title": "Cartrack verification scorecard", "facts": CARTRACK_FACTS, "items": CARTRACK},
    "ns": {"name": "Netstar", "title": "Netstar sales scorecard", "facts": NETSTAR_FACTS, "items": NETSTAR},
}

assert sum(i["weight"] for i in NETSTAR) == 220
