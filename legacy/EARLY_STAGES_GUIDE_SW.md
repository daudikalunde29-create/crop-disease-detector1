# Crop Disease Detector — mwongozo wa hatua za awali (M4.2)

## Kile kinachopatikana katika build hii

- Registration/login/logout hutumia Django session halisi; hakuna demo account wala fake authentication.
- CSRF cookie inatayarishwa kabla ya POST ya kwanza. Hili ni muhimu kwa Login, Register na Forgot Password.
- Forgot/reset password hutumia Django. Bila SMTP, reset email/link huonekana kwenye terminal ya Django wakati wa development; haitumwi inbox.
- Google Sign-In inahitaji `GOOGLE_CLIENT_ID` halisi kwenye `backend/.env`; bila hiyo imezimwa kwa uwazi.
- Profile name na phone vinaweza kusomwa/kusasishwa kupitia `GET/PUT /api/profile/`. Email ni read-only kwa sasa.
- Scan inaruhusu camera/file picker, preview na validation ya JPG/PNG/WEBP hadi 5 MB. `capture="environment"` huomba kamera ya nyuma kwenye simu zinazoiunga mkono; desktop inaweza kufungua file picker badala ya live camera.
- Dashboard, History, Admin na Result zina sample JSON iliyoandikwa wazi kuwa si data ya akaunti wala AI diagnosis.
- Submit ya Analyze Image hutuma picha kwa Django. Kwa sababu model haipo, backend inajibu `not_ready`; hakuna ugonjwa au confidence inayobuniwa.

## Windows setup

1. Install Node.js 22 LTS.
2. Install Python 3.13 (recommended) and the Python Launcher. Python 3.15 inaweza kuwa mbele ya support ya baadhi ya dependencies.
3. Extract ZIP. Fungua folder `pixel-showcase` kwenye VS Code.
4. Terminal ya kwanza, run `powershell -ExecutionPolicy Bypass -File .\setup-backend.ps1`. Setup itaunda `backend/.venv`, `.env`, migrations na kuendesha tests.
5. Run `powershell -ExecutionPolicy Bypass -File .\start-backend.ps1`; iache terminal hiyo wazi.
6. Terminal ya pili, run `powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1`; fungua `http://127.0.0.1:8080`.
7. Tengeneza akaunti yako mwenyewe kupitia Register. Usajili unahitaji Django iwe inafanya kazi.

## Demo data

`public/site/data/mock-*.json` ni data za UI pekee. Zitumie kujaribu dashboard/history/result layout. Hazijahifadhiwa kwenye database na si prediction za model. Hakuna password ya demo.

## Stages zinazofuata

- M4.2: thibitisha registration/login/session/password reset/profile kwa Django tests na browser.
- M5: MySQL database.
- M6: OpenCV preprocessing.
- M7–M8: dataset, training na inference ya TensorFlow/Keras.
- Baada ya hapo: prediction history halisi, disease knowledge, admin API, security hardening na deployment.
