# Analytiikkaputken pelikirja

Menetelmä, ei tämän projektin dokumentaatio. Tarkoitettu luettavaksi ennen
seuraavan putken aloittamista — myös eri lähdejärjestelmällä ja eri
toimialalla.

Kaikki alla oleva on opittu tekemällä väärin ensin. Kunkin säännön perässä
on se, mitä sen rikkominen maksoi.

---

## Järjestys

Numerot ovat merkitseviä. Tämä on riippuvuusjärjestys, ei tehtävälista.

**1. Nimeä yksi päätös tai toistuva tilanne, jota tämä muuttaa.**
Itsellesi, ei ääneen palaverissa. Ks. "Miten kysyä" alla.

**2. Hahmottele lopputuotos keksityillä luvuilla.**
Konkreettisesti: taulukko, ruutukaappaus, paperi. Tämä pakottaa
rakeisuuskysymyksen esiin ennen kuin mitään on rakennettu.

**3. Rinnakkain: määritelmät ja lähteen profilointi.**
Nämä eivät ole peräkkäisiä vaiheita. Jokaisen mittarin kohdalla kysy heti:
mistä sarakkeesta tämä tulee ja onko se täytetty?

**4. Päätä rakeisuus jokaiselle taululle.**
Yksi lause per taulu: "yksi rivi = yksi ___". Jos et osaa sanoa sitä,
taulu ei ole valmis suunniteltavaksi.

**5. Tekniset valinnat.**
Ks. "Tietovarasto vai ei" alla.

**6. Rakenna yksi mittari päästä päähän.**
Lähteestä ruudulle asti. Ei kerrosta kerrallaan.

**7. Täsmäytä se lähteeseen kontrollisummana.**

**8. Vasta sitten seuraava mittari.**

Kohtien 6–8 silmukka on koko menetelmä. Kaikki muu on valmistelua.

---

## Määritelmät ennen mallinnusta

Kirjoita `METRICS.md` ennen kuin kirjoitat SQL:ää. Yksi osio per
käyttöliittymässä näkyvä luku:

- UI-nimi täsmälleen kuten ruudulla
- Määritelmä yhdellä lauseella
- Tarkka kaava
- Lähdesarakkeet
- Reunatapaukset: NULL, nolla riviä, nollalla jako
- Viittaukset tiedosto:rivi -tarkkuudella

**Auktoriteettisääntö: käyttöliittymä on totuus.** Jos koodissa on
käyttämätöntä logiikkaa tai kaksi tapaa laskea sama asia, dokumentoi se
mitä UI renderöi ja merkitse ristiriita erikseen.

> **Hinta jos ohitat tämän:** neljä koodikatselmointikierrosta ja 52 vihreää
> testiä eivät löytäneet, että edistymisprosentti oli 78 prosenttiyksikköä
> väärässä. Yksi kysymys liiketoiminnalle löysi sen.

---

## Profiloi lähde, älä luota dokumentaatioon

Skeema kertoo mitä *saa* olla. Profilointi kertoo mitä *on*. Ristiriita on
aina kiinnostava.

Seitsemän kysymystä jokaiselle taululle:

| # | Kysymys | Miten |
|---|---|---|
| 1 | Elääkö taulu? | rivit aikayksiköittäin `created_at`-sarakkeesta |
| 2 | Onko avain avain? | `count(*)` vs `count(distinct avain)` |
| 3 | Onko orpoja? | left join lähdetauluun, `where pk is null` |
| 4 | Onko käyttämätöntä? | käänteinen liitos |
| 5 | Mitä arvoja siellä oikeasti on? | `group by sarake order by count desc` |
| 6 | Onko jakauma vino? | osuus per ryhmä |
| 7 | Onko arvoalue järkevä? | `SUMMARIZE taulu` |

DuckDB: `SUMMARIZE taulu;` antaa kohdat 2 ja 7 kerralla. Tärkein sarake on
`null_percentage` — 75 % NULL tarkoittaa, että sarake on olemassa mutta ei
käytössä.

> **Todellisia löydöksiä tästä projektista:** vapaa tekstikenttä `gym_name`
> sisälsi saman salin kolmella kirjoitusasulla. Yksi käyttäjä tuotti 70 %
> kaikesta datasta. `user_profiles` oli tyhjä, vaikka koko rankkijärjestelmä
> nojasi siihen.

> **Hinta jos ohitat tämän:** putki viittasi tauluun `comments`, jota ei ole
> olemassa — se on `activity_comments`. Ja neljään `user_profiles`-sarakkeeseen,
> joita ei ole. Testidata keksi molemmat, joten kaikki testit olivat vihreitä.

---

## Rakenna yksi mittari kerrallaan

Ei näin: mallinnetaan koko staging-kerros, sitten intermediate, sitten martit.

Vaan näin: yksi luku lähteestä ruudulle, täsmäytetään, sitten seuraava.

Ero on siinä, milloin integraatio-ongelmat löytyvät. Kerroksittain
rakennettaessa kuukauden kolmannella viikolla, viipaleittain kolmantena
päivänä.

Sivuvaikutus freelancerille: **ensimmäinen viipale on hinta-arvio.** Myy
discovery + yksi mittari kiinteänä. Sen jälkeen tiedät mitä loput maksavat,
ja asiakas on saanut jotain toimivaa ennen isoa sitoumusta.

---

## Täsmäytys on hyväksyntäkriteeri

Testit todistavat, että putki ajaa läpi. Vain täsmäytys todistaa, että se
laskee oikein.

Kontrollisumma: **laske sama luku kahta riippumatonta reittiä ja vaadi että
erotus on nolla.** Sama asia kuin täsmäytysvälilehden alarivi kirjanpidossa.

Ylläpidä `RECONCILIATION.md`:
- rivi per UI:ssa näkyvä luku
- mihin malliin ja sarakkeeseen se vastaa
- kaava molemmilla puolilla
- päivätyt tilannekuvat

Kartta on pysyvä, luvut ovat tilannekuvia.

> Alan käytäntö: automaattiset rivimäärä- ja skeematestit ovat yleisiä.
> Systemaattinen varasto-vastaan-lähdejärjestelmä -täsmäytys on harvinaista.
> Se on erottautumistekijä, ei perustaito.

---

## Ponytail: tarvitseeko tämän olla olemassa?

Sovella jokaiseen malliin. Kriteeri ei ole rivimäärä vaan **oma rakeisuus ja
oma vastuu.**

Yhdistämissignaalit:
- Kaksi mallia samalla rakeisuudella peräkkäin ketjussa
- Malli, joka lisää vain sarakevalinnan tai yhden lasketun kentän
- Malli, jolla on täsmälleen yksi kuluttaja ja joka ei tee liitosta

**Vastasuunta, joka pätee analytiikassa:** eksplisiittisyys voittaa
nokkeluuden. Nimetyt CTE-lohkot, joista kukin tekee yhden asian, säilyvät.
Mallien yhdistäminen ei tarkoita niiden puristamista sisäkkäisiksi
alikyselyiksi. Lyhyt ja näppärä SQL on tuskaa debugata puoli vuotta myöhemmin.

---

## Kerrokset ja materialisointi

Kolme kerrosta ei ole laki. Se on pienin määrä, joka erottaa kolme
muutostyyppiä:

| Kerros | Imee muutoksen | Materialisointi |
|---|---|---|
| staging | lähde muuttui | näkymä, 1:1 lähdetaulun kanssa, ei liitoksia |
| intermediate | sääntö muuttui | näkymä, tässä liitokset |
| marts | raportti muuttui | taulu, tässä kallis työ |

Näkymä = tallennettu kysely, ei tallennettua dataa. Taulu = tulos levyllä.
Power BI -vastine: DirectQuery vs Import.

Käytännössä tämä tarkoittaa, että 14 mallia voi olla 3 taulua ja 11 näkymää.
Kaavion visuaalinen raskaus ei vastaa sen todellista raskautta.

**Staging heijastaa lähdettä.** Se poimii kaikki sarakkeet, myös
käyttämättömät, ja dokumentoi käyttämättömyyden. Alavirran mallit valitsevat
mitä tarvitsevat. Jos optimoit stagingin alavirran tarpeisiin, se lakkaa
olemasta luotettava kuva lähteestä.

---

## Tietovarasto vai suoraan BI-työkaluun

Väärä kysymys: montako lähdettä.
Oikea kysymys: **tarvitseeko logiikan elää raporttia pidempään ja laajemmalle?**

BI-työkalu riittää: yksi raportti, yksi tekijä, yksi kuluttaja, ei historiaa,
määritelmää ei tarvitse jakaa.

Tietovarasto, kun mikä tahansa toteutuu:
- Sama määritelmä tarvitaan useassa paikassa
- Tarvitset historiaa jota lähde ei säilytä
- Useampi kehittäjä
- Logiikka pitää voida katselmoida ja testata
- Lähdejärjestelmä ei kestä kyselykuormaa

Neljä ensimmäistä kaatavat projekteja. Yksikään ei liity datan määrään.

---

## Poiminnan säännöt

**Lataa raakana, muokkaa perillä.** Jos suodatat poiminnassa, menetät datan
pysyvästi — uudelleenpoiminta ei palauta samaa tilannekuvaa, koska
tuotantokanta elää.

**Epäonnistu äänekkäästi.** Poiminta, joka nappaa poikkeuksen ja jatkaa,
jättää edellisen ajon taulun paikalleen. dbt rakentaa vanhentuneen datan
päälle, testit menevät läpi, kukaan ei huomaa.

**Tyhjä tulos ei ole virhe mutta ei myöskään onnistuminen.** Luo tyhjä taulu
oikealla sarakelistalla. Muuten alavirta kaatuu tai — pahempaa — lukee
edellisen ajon rivejä.

**Vahdi skeemadriftiä.** Testi, joka vertaa raakataulujen sarakkeita
odotettuun listaan. Tämä on se vahti, jonka puuttuminen päästi läpi
olemattoman taulunimen.

---

## Testien severity

`error` pysäyttää alavirran. `warn` ei.

| Testityyppi | Severity | Miksi |
|---|---|---|
| Avain ei ole uniikki | error | Alavirta on väärässä joka tapauksessa |
| Viite-eheys rikki | error | Liitokset tuottavat vääriä rivejä |
| Lähdejärjestelmän ajautuminen | **warn** | Signaali, ei syy jättää dashboardit päivittämättä |
| Lähdejärjestelmän bugi | **warn** | Paljasta se, älä pysähdy siihen |

> **Hinta väärästä valinnasta:** yksi poikkeava rivi staging-tason testissä
> ohitti 31 alavirran solmua. Yhtään marttia ei rakennettu.

---

## Miten kysyä liiketoiminnalta

Yllä oleva järjestys on kuvaus siitä mitä sinun pitää **tietää** — ei
käsikirjoitus palaveriin. Sana "rakeisuus" ei tarvitse tulla ääneen
kertaakaan.

| Älä kysy | Kysy |
|---|---|
| Mitä päätöstä tämä muuttaa? | Milloin viimeksi katsoit tätä lukua ja teit jotain? |
| Mitkä ovat tavoitteesi? | Mistä sinulle soitetaan kun jokin on pielessä? |
| Mitä mittareita tarvitset? | Mitä teet nyt käsin Excelissä? |
| Mikä on tärkein mittari? | Mihin lukuun et nykyisessä raportissa luota? |

**Tule hypoteesin kanssa, älä kysymyksen.** Seniorit korjaavat nopeammin kuin
määrittelevät. Väärä väite tuottaa kaksikymmentä sekuntia ja tarkan
vastauksen; avoin kysymys kymmenen minuuttia ja olankohautuksen.

**Näytä väärä luku tarkoituksella.** Ihmiset reagoivat paremmin kuin
spesifioivat.

---

## LLM-avusteinen kehitys

| Hyvä | Huono |
|---|---|
| Muunnoslogiikan SQL | Tietämään mitä liiketoiminta tarkoittaa |
| Testien generointi | Päättämään rakeisuuden |
| Dokumentaation kirjoittaminen | Valitsemaan kahdesta uskottavasta määritelmästä |
| Tuntemattoman skeeman haravointi | Tietämään mikä luku on oikein |

Kun SQL:n kirjoittaminen halpenee, ihmisen työ ei vähene — se **siirtyy**
määrittelyyn ja täsmäytykseen.

Käytännön varotoimi: LLM tuottaa itsevarmoja vääriä tuloksia. Tässä
projektissa kaksi kolmesta semanttisesta löydöksestä oli väärin, ja ne
kumoutuivat vasta kun määrittelydokumentti kirjoitettiin.
