import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.module.js";

const ECHELLE = 1 / 40;
const AIDE_ROTATION = "Glissez pour tourner · boutons + et − pour zoomer · survolez une table";
const AIDE_DEPLACEMENT = "Glissez une table ou un élément pour le placer";

const matiere = (couleur, options = {}) => new THREE.MeshStandardMaterial({ color: couleur, roughness: 0.75, ...options });

function piece(groupe, geometrie, materiau, x, y, z) {
    const maille = new THREE.Mesh(geometrie, materiau);
    maille.position.set(x, y, z);
    maille.castShadow = true;
    maille.receiveShadow = true;
    groupe.add(maille);
    return maille;
}

function boite(groupe, largeur, hauteur, profondeur, materiau, x, y, z) {
    return piece(groupe, new THREE.BoxGeometry(largeur, hauteur, profondeur), materiau, x, y, z);
}

function etiquette(groupe, texte, hauteur) {
    const toile = document.createElement("canvas");
    toile.width = 512;
    toile.height = 112;
    const contexte = toile.getContext("2d");
    contexte.fillStyle = "rgba(255, 255, 255, 0.92)";
    contexte.fillRect(16, 16, 480, 80);
    contexte.strokeStyle = "#B8975A";
    contexte.lineWidth = 3;
    contexte.strokeRect(16, 16, 480, 80);
    contexte.fillStyle = "#141210";
    contexte.font = "500 60px Jost, Arial, sans-serif";
    contexte.textAlign = "center";
    contexte.textBaseline = "middle";
    contexte.fillText(texte, 256, 58, 460);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(toile), depthTest: false, transparent: true }));
    sprite.position.y = hauteur;
    sprite.scale.set(2.7, 0.59, 1);
    sprite.name = "etiquette";
    sprite.renderOrder = 1;
    groupe.add(sprite);
}

function chaise(groupe, x, z, angle, occupee) {
    const siege = new THREE.Group();
    const materiau = occupee ? matiere("#B8975A", { metalness: 0.35, roughness: 0.45 }) : matiere("#F1ECE4");
    boite(siege, 0.42, 0.06, 0.42, materiau, 0, 0.46, 0);
    boite(siege, 0.42, 0.5, 0.05, materiau, 0, 0.72, 0.2);
    [-0.17, 0.17].forEach((cote) => [-0.17, 0.17].forEach((fond) => boite(siege, 0.04, 0.44, 0.04, materiau, cote, 0.22, fond)));
    siege.position.set(x, 0, z);
    siege.rotation.y = angle;
    groupe.add(siege);
}

function centreDeTable(groupe, x, accent) {
    piece(groupe, new THREE.CylinderGeometry(0.07, 0.09, 0.26, 16), matiere("#FFFFFF", { transparent: true, opacity: 0.7 }), x, 0.92, 0);

    for (let index = 0; index < 5; index += 1) {
        const angle = (index / 5) * Math.PI * 2;
        piece(
            groupe, new THREE.SphereGeometry(0.1, 14, 10), matiere(index % 2 ? "#FFFFFF" : accent),
            x + Math.cos(angle) * 0.11, 1.09 + (index % 2) * 0.06, Math.sin(angle) * 0.11
        );
    }

    piece(groupe, new THREE.SphereGeometry(0.11, 14, 10), matiere("#5E7A5A"), x, 1.06, 0);
}

function construireTable(groupe, table, couleurs) {
    const nappe = matiere(couleurs.nappe, { side: THREE.DoubleSide });
    const accent = matiere(couleurs.accent);
    const largeur = table.largeur * ECHELLE;
    const profondeur = table.profondeur * ECHELLE;

    if (table.forme === "Ronde") {
        const rayon = largeur / 2;
        piece(groupe, new THREE.CylinderGeometry(rayon, rayon, 0.05, 48), nappe, 0, 0.76, 0);
        piece(groupe, new THREE.CylinderGeometry(rayon, rayon + 0.08, 0.72, 48, 1, true), nappe, 0, 0.39, 0);
        piece(groupe, new THREE.CylinderGeometry(rayon * 0.4, rayon * 0.4, 0.01, 40), accent, 0, 0.795, 0);

        for (let place = 0; place < table.places; place += 1) {
            const angle = (place / table.places) * Math.PI * 2;
            chaise(groupe, Math.cos(angle) * (rayon + 0.35), Math.sin(angle) * (rayon + 0.35), Math.PI / 2 - angle, place < table.occupees);
        }

        centreDeTable(groupe, 0, couleurs.accent);
        return;
    }

    boite(groupe, largeur, 0.05, profondeur, nappe, 0, 0.76, 0);
    boite(groupe, largeur + 0.04, 0.72, profondeur + 0.04, nappe, 0, 0.38, 0);
    boite(groupe, largeur, 0.01, profondeur * 0.3, accent, 0, 0.795, 0);
    const parCote = table.honneur ? table.places : Math.ceil(table.places / 2);

    for (let place = 0; place < table.places; place += 1) {
        const auFond = place < parCote;
        const rang = auFond ? place : place - parCote;
        const x = -largeur / 2 + (largeur / parCote) * (rang + 0.5);
        chaise(groupe, x, (auFond ? -1 : 1) * (profondeur / 2 + 0.3), auFond ? Math.PI : 0, place < table.occupees);
    }

    const bouquets = Math.max(1, Math.round(largeur / 3));

    for (let index = 0; index < bouquets; index += 1) {
        centreDeTable(groupe, -largeur / 2 + (largeur / bouquets) * (index + 0.5), couleurs.accent);
    }
}

const ELEMENTS = {
    "Piste de danse": (groupe, l, p, couleurs) => {
        boite(groupe, l, 0.04, p, matiere("#2A2622", { metalness: 0.5, roughness: 0.25 }), 0, 0.02, 0);
        boite(groupe, l + 0.1, 0.03, p + 0.1, matiere(couleurs.accent, { metalness: 0.4 }), 0, 0.01, 0);
    },
    "DJ": (groupe, l, p, couleurs) => {
        boite(groupe, l, 1.05, p * 0.6, matiere("#141210"), 0, 0.53, 0);
        boite(groupe, l, 0.04, p * 0.62, matiere(couleurs.accent, { metalness: 0.5 }), 0, 1.07, 0);
        [-0.5, 0.5].forEach((cote) => {
            piece(groupe, new THREE.CylinderGeometry(0.17, 0.17, 0.05, 28), matiere("#4A443D"), cote, 1.12, 0);
            boite(groupe, 0.4, 1.5, 0.4, matiere("#1E1B18"), cote * (l + 0.5), 0.75, 0);
            piece(groupe, new THREE.CylinderGeometry(0.14, 0.14, 0.02, 24), matiere("#6B645C"), cote * (l + 0.5), 1.1, 0.21).rotation.x = Math.PI / 2;
        });
    },
    "Buffet": (groupe, l, p, couleurs) => {
        boite(groupe, l, 0.9, p, matiere(couleurs.nappe), 0, 0.45, 0);

        for (let plat = 0; plat < 6; plat += 1) {
            piece(
                groupe, new THREE.CylinderGeometry(0.2, 0.15, 0.1, 24), matiere(plat % 2 ? couleurs.accent : "#E6DFD4", { metalness: 0.3 }),
                0, 0.96, -p / 2 + (plat + 0.5) * (p / 6)
            );
        }
    },
    "Bar": (groupe, l, p, couleurs) => {
        boite(groupe, l * 0.7, 1.1, p, matiere("#3B2F26"), 0, 0.55, 0);
        boite(groupe, l, 0.06, p + 0.1, matiere(couleurs.accent, { metalness: 0.4, roughness: 0.35 }), 0, 1.13, 0);

        for (let verre = 0; verre < 8; verre += 1) {
            piece(
                groupe, new THREE.CylinderGeometry(0.05, 0.03, 0.2, 14), matiere("#FFFFFF", { transparent: true, opacity: 0.6 }),
                0, 1.26, -p / 2 + (verre + 0.5) * (p / 8)
            );
        }
    },
    "Photobooth": (groupe, l, p, couleurs) => {
        boite(groupe, l, 2.2, 0.06, matiere(couleurs.accent), 0, 1.1, -p / 2);
        boite(groupe, 0.3, 1.4, 0.3, matiere("#141210"), 0, 0.7, p / 2);
    },
    "Arche": (groupe, l, p, couleurs) => {
        const rayon = l / 2 - 0.1;
        const arc = piece(groupe, new THREE.TorusGeometry(rayon, 0.06, 12, 48, Math.PI), matiere(couleurs.accent, { metalness: 0.4 }), 0, 1.2, 0);
        arc.rotation.y = 0;
        [-rayon, rayon].forEach((cote) => piece(groupe, new THREE.CylinderGeometry(0.06, 0.06, 1.2, 12), matiere(couleurs.accent, { metalness: 0.4 }), cote, 0.6, 0));

        for (let fleur = 0; fleur <= 18; fleur += 1) {
            const angle = (fleur / 18) * Math.PI;
            const teinte = ["#FFFFFF", "#5E7A5A", couleurs.accent][fleur % 3];
            piece(groupe, new THREE.SphereGeometry(0.13, 12, 10), matiere(teinte), Math.cos(angle) * rayon, 1.2 + Math.sin(angle) * rayon, 0);
        }
    },
    "Gâteau": (groupe, l, p, couleurs) => {
        piece(groupe, new THREE.CylinderGeometry(l / 2, l / 2, 0.75, 36), matiere(couleurs.nappe), 0, 0.38, 0);
        [0.36, 0.27, 0.18].forEach((rayon, etage) => {
            piece(groupe, new THREE.CylinderGeometry(rayon, rayon, 0.24, 36), matiere("#FFFDF8"), 0, 0.88 + etage * 0.26, 0);
            piece(groupe, new THREE.CylinderGeometry(rayon + 0.01, rayon + 0.01, 0.04, 36), matiere(couleurs.accent), 0, 0.79 + etage * 0.26, 0);
        });
    }
};

const HAUTEURS = { "Piste de danse": 0.6, "Arche": 3.1, "Photobooth": 2.6, "Gâteau": 1.9 };

function liberer(groupe) {
    groupe.traverse((noeud) => {
        if (noeud.geometry) noeud.geometry.dispose();
        if (noeud.material) {
            if (noeud.material.map) noeud.material.map.dispose();
            noeud.material.dispose();
        }
    });
}

function creerSalle(racine) {
    const cadre = racine.querySelector(".scene");
    const bulle = racine.querySelector(".bulle");
    const aide = racine.querySelector(".aide");
    const boutons = Object.fromEntries([...racine.querySelectorAll("button")].map((bouton) => [bouton.dataset.action, bouton]));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
    const rendu = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    rendu.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    rendu.shadowMap.enabled = true;
    rendu.shadowMap.type = THREE.PCFSoftShadowMap;
    cadre.appendChild(rendu.domElement);

    const ciel = new THREE.HemisphereLight("#FFFFFF", "#CDBFA8", 0.72);
    const soleil = new THREE.DirectionalLight("#FFF4E6", 0.38);
    soleil.position.set(-12, 20, 12);
    soleil.castShadow = true;
    soleil.shadow.mapSize.set(2048, 2048);
    soleil.shadow.bias = -0.0005;
    Object.assign(soleil.shadow.camera, { left: -28, right: 28, top: 28, bottom: -28, far: 80 });
    scene.add(ciel, soleil);

    const orbite = { cible: new THREE.Vector3(0, 0.5, 0), tour: 0, hauteur: 0.8, distance: 28 };
    const rayon = new THREE.Raycaster();
    const sol = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    const souris = new THREE.Vector2();
    let donnees = null;
    let contenu = null;
    let guirlandes = null;
    let objets = [];
    let mode = { deplacer: false, soiree: false };
    let geste = null;
    let envoyer = () => {};
    let boucle = 0;
    let etiquettesVisibles = true;

    const versX = (x) => (x - donnees.largeur / 2) * ECHELLE;
    const versZ = (y) => (y - donnees.profondeur / 2) * ECHELLE;

    function placerCamera() {
        const { cible, tour, hauteur, distance } = orbite;
        camera.position.set(
            cible.x + distance * Math.cos(hauteur) * Math.sin(tour),
            cible.y + distance * Math.sin(hauteur),
            cible.z + distance * Math.cos(hauteur) * Math.cos(tour)
        );
        camera.lookAt(cible);
    }

    function distancePour(marge) {
        const taille = Math.max(donnees.profondeur * ECHELLE * 1.15, (donnees.largeur * ECHELLE) / Math.max(camera.aspect, 0.6));
        return (taille / 2 / Math.tan((camera.fov / 2) * (Math.PI / 180))) * marge;
    }

    const vues = {
        ensemble: () => Object.assign(orbite, { tour: 0, hauteur: 0.78, distance: distancePour(1.12) }) && orbite.cible.set(0, 0, 0),
        dessus: () => Object.assign(orbite, { tour: 0, hauteur: Math.PI / 2 - 0.01, distance: distancePour(1.1) }) && orbite.cible.set(0, 0, 0),
        invite: () => {
            const tables = donnees.objets.filter((objet) => objet.genre === "table" && !objet.honneur);
            const table = tables[tables.length - 1] || donnees.objets[0];
            Object.assign(orbite, { tour: Math.atan2(versX(table.x), versZ(table.y) + donnees.profondeur * ECHELLE), hauteur: 0.06, distance: 5 });
            orbite.cible.set(versX(table.x) * 0.8, 1.1, versZ(table.y) - 3.2);
        }
    };

    function ambiance() {
        scene.background = new THREE.Color(mode.soiree ? "#1B1714" : "#FAF7F2");
        ciel.intensity = mode.soiree ? 0.3 : 0.72;
        soleil.intensity = mode.soiree ? 0.08 : 0.38;
        if (guirlandes) guirlandes.visible = mode.soiree;
    }

    function montrerEtiquettes(visibles) {
        etiquettesVisibles = visibles;
        objets.forEach((groupe) => { groupe.getObjectByName("etiquette").visible = visibles; });
    }

    function construireDecor(l, p) {
        piece(contenu, new THREE.PlaneGeometry(l, p), matiere("#DCC8A8"), 0, 0, 0).rotation.x = -Math.PI / 2;
        const murs = matiere("#F4EEE4");
        boite(contenu, l + 0.2, 2.8, 0.15, murs, 0, 1.4, -p / 2 - 0.08).castShadow = false;
        boite(contenu, 0.15, 2.8, p, murs, -l / 2 - 0.08, 1.4, 0).castShadow = false;
        boite(contenu, 0.15, 2.8, p, murs, l / 2 + 0.08, 1.4, 0).castShadow = false;

        guirlandes = new THREE.Group();
        const ampoule = matiere("#FFD9A0", { emissive: "#FFB955", emissiveIntensity: 1.6 });

        for (let fil = 0; fil < 4; fil += 1) {
            const z = -p / 2 + (fil + 0.5) * (p / 4);

            for (let index = 0; index <= 22; index += 1) {
                const t = index / 22;
                const boule = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 8), ampoule);
                boule.position.set(-l / 2 + t * l, 2.9 - Math.sin(t * Math.PI) * 0.5, z);
                guirlandes.add(boule);
            }

            const halo = new THREE.PointLight("#FFC27A", 0.6, 22, 1.2);
            halo.position.set(0, 2.5, z);
            guirlandes.add(halo);
        }

        contenu.add(guirlandes);
    }

    function construire(nouvelles) {
        const premiere = !donnees;
        const changeTaille = donnees && donnees.profondeur !== nouvelles.profondeur;
        donnees = nouvelles;

        if (contenu) {
            scene.remove(contenu);
            liberer(contenu);
        }

        contenu = new THREE.Group();
        objets = [];
        construireDecor(donnees.largeur * ECHELLE, donnees.profondeur * ECHELLE);

        donnees.objets.forEach((objet) => {
            const groupe = new THREE.Group();

            if (objet.genre === "table") {
                construireTable(groupe, objet, donnees.couleurs);
            } else {
                ELEMENTS[objet.nom](groupe, objet.largeur * ECHELLE, objet.profondeur * ECHELLE, donnees.couleurs);
            }

            etiquette(groupe, objet.nom, HAUTEURS[objet.nom] || 1.85);
            groupe.position.set(versX(objet.x), 0, versZ(objet.y));
            groupe.userData = objet;
            objets.push(groupe);
            contenu.add(groupe);
        });

        scene.add(contenu);
        ambiance();
        montrerEtiquettes(etiquettesVisibles);

        if (premiere || changeTaille) {
            dimensionner();
            vues.ensemble();
        }
    }

    function dimensionner() {
        const largeur = cadre.parentElement.clientWidth || 800;
        const hauteur = cadre.parentElement.clientHeight || 600;
        camera.aspect = largeur / hauteur;
        camera.updateProjectionMatrix();
        rendu.setSize(largeur, hauteur);
    }

    function viser(evenement) {
        const zone = rendu.domElement.getBoundingClientRect();
        souris.set(((evenement.clientX - zone.left) / zone.width) * 2 - 1, -((evenement.clientY - zone.top) / zone.height) * 2 + 1);
        rayon.setFromCamera(souris, camera);
    }

    function objetVise(evenement) {
        viser(evenement);
        const touche = rayon.intersectObjects(objets, true)[0];
        let noeud = touche && touche.object;

        while (noeud && !objets.includes(noeud)) noeud = noeud.parent;

        return noeud || null;
    }

    function pointAuSol(evenement) {
        viser(evenement);
        return rayon.ray.intersectPlane(sol, new THREE.Vector3());
    }

    function montrerBulle(evenement) {
        const vise = objetVise(evenement);

        if (!vise || vise.userData.genre !== "table") {
            bulle.style.display = "none";
            return;
        }

        const table = vise.userData;
        const zone = rendu.domElement.getBoundingClientRect();
        const titre = document.createElement("strong");
        titre.textContent = table.nom;
        bulle.replaceChildren(titre, `${table.occupees}/${table.places} places · ${table.invites.slice(0, 12).join(", ") || "personne pour l'instant"}`);
        bulle.style.display = "block";
        bulle.style.left = `${Math.min(evenement.clientX - zone.left + 16, zone.width - 270)}px`;
        bulle.style.top = `${Math.min(evenement.clientY - zone.top + 16, zone.height - 110)}px`;
    }

    const borner = (valeur, taille, total) => Math.min(Math.max(valeur, taille / 2 + donnees.marge), total - taille / 2 - donnees.marge);

    function appuyer(evenement) {
        const vise = mode.deplacer ? objetVise(evenement) : null;
        const point = vise && pointAuSol(evenement);
        rendu.domElement.setPointerCapture(evenement.pointerId);
        geste = vise && point
            ? { groupe: vise, ecart: point.sub(vise.position) }
            : { x: evenement.clientX, y: evenement.clientY };
        bulle.style.display = "none";
    }

    function bouger(evenement) {
        if (!geste) {
            montrerBulle(evenement);
            return;
        }

        if (geste.groupe) {
            const point = pointAuSol(evenement);
            if (!point) return;
            const objet = geste.groupe.userData;
            const x = borner((point.x - geste.ecart.x) / ECHELLE + donnees.largeur / 2, objet.largeur, donnees.largeur);
            const y = borner((point.z - geste.ecart.z) / ECHELLE + donnees.profondeur / 2, objet.profondeur, donnees.profondeur);
            geste.groupe.position.set(versX(x), 0.12, versZ(y));
            geste.position = { x: Math.round(x), y: Math.round(y) };
            return;
        }

        orbite.tour -= (evenement.clientX - geste.x) * 0.006;
        orbite.hauteur = Math.min(Math.max(orbite.hauteur + (evenement.clientY - geste.y) * 0.005, 0.05), Math.PI / 2 - 0.01);
        geste.x = evenement.clientX;
        geste.y = evenement.clientY;
    }

    function relacher() {
        if (geste && geste.groupe) {
            geste.groupe.position.y = 0;
            if (geste.position) envoyer({ nom: geste.groupe.userData.nom, ...geste.position });
        }

        geste = null;
    }

    function zoomer(facteur) {
        orbite.distance = Math.min(Math.max(orbite.distance * facteur, 3), 70);
    }

    function basculer(nom) {
        mode = { ...mode, [nom]: !mode[nom] };
        boutons[nom].setAttribute("aria-pressed", String(mode[nom]));
        aide.textContent = mode.deplacer ? AIDE_DEPLACEMENT : AIDE_ROTATION;
        rendu.domElement.style.cursor = mode.deplacer ? "move" : "grab";
        ambiance();
    }

    function telecharger() {
        rendu.render(scene, camera);
        const lien = document.createElement("a");
        lien.href = rendu.domElement.toDataURL("image/png");
        lien.download = "salle.png";
        lien.click();
    }

    const actions = {
        deplacer: () => basculer("deplacer"),
        soiree: () => basculer("soiree"),
        plus: () => zoomer(0.85),
        moins: () => zoomer(1.18),
        image: telecharger,
        ensemble: () => { vues.ensemble(); montrerEtiquettes(true); },
        dessus: () => { vues.dessus(); montrerEtiquettes(true); },
        invite: () => { vues.invite(); montrerEtiquettes(false); }
    };
    Object.entries(boutons).forEach(([nom, bouton]) => { bouton.onclick = actions[nom]; });
    aide.textContent = AIDE_ROTATION;
    rendu.domElement.style.cursor = "grab";
    rendu.domElement.addEventListener("pointerdown", appuyer);
    rendu.domElement.addEventListener("pointermove", bouger);
    rendu.domElement.addEventListener("pointerup", relacher);
    rendu.domElement.addEventListener("pointercancel", relacher);
    rendu.domElement.addEventListener("pointerleave", () => { bulle.style.display = "none"; });
    const observateur = new ResizeObserver(() => donnees && dimensionner());
    observateur.observe(cadre.parentElement);

    (function animer() {
        boucle = requestAnimationFrame(animer);
        if (!donnees) return;
        placerCamera();
        rendu.render(scene, camera);
    })();

    return {
        actualiser(nouvelles, rappel) {
            envoyer = rappel;
            const signature = JSON.stringify(nouvelles);
            if (signature === this.signature) return;
            this.signature = signature;
            construire(nouvelles);
        },
        fermer() {
            cancelAnimationFrame(boucle);
            observateur.disconnect();
            if (contenu) liberer(contenu);
            rendu.dispose();
            rendu.domElement.remove();
        }
    };
}

const salles = new WeakMap();

export default function ({ data, parentElement, setTriggerValue }) {
    const racine = parentElement.querySelector(".salle");

    if (!salles.has(racine)) {
        try {
            salles.set(racine, creerSalle(racine));
        } catch (erreur) {
            racine.querySelector(".aide").textContent = "La 3D n'est pas disponible dans ce navigateur (WebGL désactivé).";
            return undefined;
        }
    }

    const salle = salles.get(racine);
    salle.actualiser(data, (deplacement) => setTriggerValue("deplacement", deplacement));

    return () => {
        salle.fermer();
        salles.delete(racine);
    };
}
