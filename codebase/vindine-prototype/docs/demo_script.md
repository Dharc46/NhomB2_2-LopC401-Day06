# Demo Script

## Run Backend

```powershell
cd C:\Users\Lenovo\Day06-C401-NhomE5\codebase\vindine-prototype
py -m uvicorn src.api:app --reload
```

## Run Frontend

```powershell
cd C:\Users\Lenovo\Day06-C401-NhomE5\codebase\vindine-prototype
py -m streamlit run src/app.py
```

## Four Demo Flows

Happy path:
`Nha minh 6 nguoi o sanh Vinpearl, co ong ba va 2 tre em, muon mon Viet hoac pizza, co voucher buffet, di bo duoi 8 phut.`

Low confidence:
`Co voucher Vin, tim quan gan gan cho gia dinh.`

Failure/conflict:
`7 nguoi, co ong ba, muon yen tinh, co tre em, dung voucher buffet, duoi 70k/nguoi.`

Correction/re-rank:
First ask: `6 nguoi, co tre em, muon an nhanh gan sanh.`
Then reject a card with reason `too_noisy` in the UI.

## Notes

- Dataset is mock/synthetic for prototype use.
- Google Maps links are placeholder search links, not verified addresses.
- AI augments the decision; the group representative decides.
