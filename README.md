# INAZUMA MOVES DATABASE

Database universale `playerId -> mosse apprese`, separato da InaCodex e dal gioco.

## Output

- `data/PLAYER_MOVES_DATABASE.json` — lookup diretto tramite `playerId` / `inagle_no`.
- `data/SKILLS_DATABASE.json` — metadati delle tecniche per `skillId`.
- `reports/full_extraction_report.json` — diagnostica completa dell'estrazione.
- `scripts/extract_full_database.py` — estrattore riproducibile.

## Fonti

- Ownership e mapping `inagle_no -> character_id`: `https://inazuma-eleven-db.vercel.app/`
- Nomi inglesi verificabili: cataloghi Inagle/Zukan JP e EN, associati nella stessa posizione del catalogo ufficiale.

## Ultima estrazione validata

- 5.478 righe personaggio sorgente.
- 5.456 `inagle_no` unici risolti.
- 5.456/5.456 pagine ownership risolte, 0 errori.
- 919 tecniche sorgente.
- 28.999 associazioni personaggio -> tecnica.
- 0 riferimenti a skill sconosciute.
- 27 tecniche senza un nome inglese ufficiale univocamente verificabile: il nome inglese resta `null`, non viene inventato.

Gli ID alti sono stati verificati esplicitamente: `4487 -> c07060110` e `4507 -> c07070020`.
