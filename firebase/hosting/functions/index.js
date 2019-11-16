const admin = require('firebase-admin');
const functions = require('firebase-functions');
const express = require('express');
const engines = require('consolidate');

// Configure Firestore
admin.initializeApp(functions.config().firebase);

let db = admin.firestore();



// Configure Express
const app = express();
app.engine('hbs', engines.handlebars);
app.set('views', './views');
app.set('view engine', 'hbs');


// Express Functions
app.get('/onboard/*', (request, response) => {
    const sessionID = request.url.split('/')[2];

    // Check for Session ID in Firestore
    let sessionReference = db.collection('dev').doc(sessionID);
    let sessionDoc = sessionReference.get()
        .then(doc => {
            // eslint-disable-next-line promise/always-return
            if (!doc.exists) {
                response.redirect('/?invalid');
            } else {
                if (!doc.get("shareAnswer")) {
                    response.render('onboarding', {id: sessionID});
                } else {
                    response.redirect("/share/" + sessionID);
                }
                
            }
        })
        .catch(error =>{
            console.log("Session ID " + sessionID + " returned an error:");
            console.log(error);
            response.redirect('/?serverError');
        });
});

app.get('/share/*', (request, response) => {
    const sessionID = request.url.split('/')[2];
    response.render('sharing', {id: sessionID});
});

app.get('/keep/*', (request, response) => {
    const sessionID = request.url.split('/')[2];
    let sessionReference = db.collection('dev').doc(sessionID);
    let sessionDoc = sessionReference.get()
        .then(doc => {
            // eslint-disable-next-line promise/always-return
            if (!doc.exists) {
                response.redirect('/?invalid');
            } else {
                sessionReference.set({
                    shareAnswer : true
                }, {merge : true});
                response.redirect("/share/" + sessionID)
            }
        })
        .catch(error =>{
            console.log("Session ID " + sessionID + " returned an error:");
            console.log(error);
            response.redirect('/?serverError');
        });
});

app.get('/add/*', (request, response) => {
    const sessionID = request.url.split('/')[2];
    let sessionReference = db.collection('dev').doc(sessionID);
    let sessionDoc = sessionReference.get()
        .then(doc => {
            // eslint-disable-next-line promise/always-return
            if (!doc.exists) {
                response.redirect('/?invalid');
            } else {
                sessionReference.set({
                    shareAnswer : true,
                    galleryVisible : true
                }, {merge : true});
                response.redirect("/share/" + sessionID)
            }
        })
        .catch(error =>{
            console.log("Session ID " + sessionID + " returned an error:");
            console.log(error);
            response.redirect('/?serverError');
        });
});

// Firebase Cloud Function Declaration
exports.onboarding = functions.https.onRequest(app);
exports.sharing = functions.https.onRequest(app);
exports.addGallery = functions.https.onRequest(app);
exports.keepPrivate = functions.https.onRequest(app);