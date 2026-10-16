/* =========================================================
   language.js — English / Kiswahili support (Vanilla JS).
   Selected language is stored in localStorage ("cdd_language").
   ========================================================= */

/* ---------------------------------------------------------
   1. Language support (English / Kiswahili)
   The selected language is stored in localStorage.
   Any element with data-i18n="key" gets translated.
   --------------------------------------------------------- */
var TRANSLATIONS = {
  en: {
    demoNotice:
      "Demo result: this prediction uses mock data. Real AI analysis will be connected later.",
    lowTitle: "We are not confident enough to identify this condition.",
    email: "Email",
    phone: "Phone",
    fullName: "Full name",
    password: "Password",
    confirmPassword: "Confirm password",
    saveChanges: "Save changes",
    language: "Language",
    totalUsers: "Total Users",
    adminDashboard: "Admin Dashboard",
    stageUpload: "Uploading image…",
    stagePrepare: "Preparing image…",
    stageAnalyze: "Running AI analysis…",
    stageResult: "Preparing result…",
    brand: "Crop Disease Detector",
    home: "Home",
    about: "About",
    howItWorks: "How It Works",
    supportedCrops: "Supported Crops",
    login: "Login",
    register: "Register",
    logout: "Logout",
    heroTitle: "Detect Crop Diseases with AI",
    heroText: "Upload or capture a crop image and get an AI-assisted disease prediction.",
    scanCrop: "Scan Your Crop",
    learnMore: "Learn More",
    dashboard: "Dashboard",
    newScan: "New Scan",
    scanHistory: "Scan History",
    profile: "Profile",
    welcome: "Welcome, Farmer",
    totalScans: "Total Scans",
    healthyCrops: "Healthy Crops",
    diseasesDetected: "Diseases Detected",
    lastScan: "Last Scan",
    recentScans: "Recent Scans",
    takePhoto: "Take Photo",
    uploadImage: "Upload Image",
    analyze: "Analyze Image",
    remove: "Remove",
    result: "Result",
    confidence: "Confidence",
    symptoms: "Symptoms",
    management: "Management",
    prevention: "Prevention",
    rememberMe: "Remember me",
    forgotPassword: "Forgot Password?",
    resetPassword: "Reset Password",
    changePassword: "Change Password",
    continueWithGoogle: "Continue with Google",
    googleNeedsSetup: "Continue with Google (needs backend setup)",
    orContinueWith: "or continue with",
    acceptTerms: "I accept the terms of use",
    sendResetLink: "Send Reset Link",
    currentPassword: "Current Password",
    newPassword: "New Password",
    accountType: "Account Type",
    provider: "Sign-in Method",
    memberSince: "Member Since",
  },
  sw: {
    demoNotice:
      "Matokeo ya majaribio: utabiri huu unatumia data ya mfano. Uchambuzi halisi wa AI utaunganishwa baadaye.",
    lowTitle: "Hatuna uhakika wa kutosha kutambua hali hii.",
    email: "Barua pepe",
    phone: "Simu",
    fullName: "Jina kamili",
    password: "Nenosiri",
    confirmPassword: "Thibitisha nenosiri",
    saveChanges: "Hifadhi mabadiliko",
    language: "Lugha",
    totalUsers: "Jumla ya Watumiaji",
    adminDashboard: "Dashibodi ya Msimamizi",
    stageUpload: "Inapakia picha…",
    stagePrepare: "Inaandaa picha…",
    stageAnalyze: "Inaendesha uchambuzi wa AI…",
    stageResult: "Inaandaa matokeo…",
    brand: "Kigunduzi cha Magonjwa ya Mazao",
    home: "Mwanzo",
    about: "Kuhusu",
    howItWorks: "Jinsi Inavyofanya Kazi",
    supportedCrops: "Mazao Yanayohudumiwa",
    login: "Ingia",
    register: "Jisajili",
    logout: "Toka",
    heroTitle: "Gundua Magonjwa ya Mazao kwa AI",
    heroText: "Pakia au piga picha ya zao lako upate utabiri wa ugonjwa kwa msaada wa AI.",
    scanCrop: "Skani Zao Lako",
    learnMore: "Jifunze Zaidi",
    dashboard: "Dashibodi",
    newScan: "Skani Mpya",
    scanHistory: "Historia ya Skani",
    profile: "Wasifu",
    welcome: "Karibu, Mkulima",
    totalScans: "Jumla ya Skani",
    healthyCrops: "Mazao Yenye Afya",
    diseasesDetected: "Magonjwa Yaliyogundulika",
    lastScan: "Skani ya Mwisho",
    recentScans: "Skani za Karibuni",
    takePhoto: "Piga Picha",
    uploadImage: "Pakia Picha",
    analyze: "Chambua Picha",
    remove: "Ondoa",
    result: "Matokeo",
    confidence: "Uhakika",
    symptoms: "Dalili",
    management: "Udhibiti",
    prevention: "Kinga",
    rememberMe: "Nikumbuke",
    forgotPassword: "Umesahau Nenosiri?",
    resetPassword: "Weka Nenosiri Jipya",
    changePassword: "Badilisha Nenosiri",
    continueWithGoogle: "Endelea na Google",
    googleNeedsSetup: "Endelea na Google (inahitaji backend)",
    orContinueWith: "au endelea na",
    acceptTerms: "Nakubali masharti ya matumizi",
    sendResetLink: "Tuma Kiungo cha Kubadilisha",
    currentPassword: "Nenosiri la Sasa",
    newPassword: "Nenosiri Jipya",
    accountType: "Aina ya Akaunti",
    provider: "Njia ya Kuingia",
    memberSince: "Mwanachama Tangu",
  },
};

function getLanguage() {
  return localStorage.getItem("cdd_language") || "en";
}

function setLanguage(lang) {
  localStorage.setItem("cdd_language", lang);
  applyLanguage();
}

function applyLanguage() {
  var lang = getLanguage();
  var dictionary = TRANSLATIONS[lang] || TRANSLATIONS.en;

  var nodes = document.querySelectorAll("[data-i18n]");
  for (var i = 0; i < nodes.length; i++) {
    var key = nodes[i].getAttribute("data-i18n");
    if (dictionary[key]) {
      nodes[i].textContent = dictionary[key];
    }
  }

  var buttons = document.querySelectorAll("[data-lang]");
  for (var j = 0; j < buttons.length; j++) {
    var isActive = buttons[j].getAttribute("data-lang") === lang;
    buttons[j].classList.toggle("btn-green", isActive);
    buttons[j].classList.toggle("btn-outline-green", !isActive);
  }
}
