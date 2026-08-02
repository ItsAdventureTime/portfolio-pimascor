# PIMASCOR PWA installation guide

PIMASCOR is a Progressive Web App. Installing it adds a dedicated PIMASCOR
icon to the device and opens the protected workspace in an app-like window.
The install reminder is intentionally compact, dismissible for 14 days, and
hidden after the browser reports that the app is installed.

## iPhone or iPad

Use Safari for the installation step:

1. Open `https://delegateops.business/pimascor/` in Safari.
2. Tap **Share**.
3. Choose **Add to Home Screen**.
4. Enable **Open as Web App** if that option is shown.
5. Tap **Add**, then open PIMASCOR from the new Home Screen icon.

This follows [Apple's iPhone guide](https://support.apple.com/en-ca/guide/iphone/iphea86e5236/ios)
and [Safari web application guidance](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications.html).

## Android

Use Chrome for the installation step:

1. Open `https://delegateops.business/pimascor/` in Chrome.
2. Tap the **⋮** menu beside the address bar.
3. Choose **Add to home screen** or **Install app**.
4. Confirm **Install**.

This follows [Google Chrome's current Android web-app instructions](https://support.google.com/chrome/answer/9658361/use-progressive-web-apps-android?co=GENIE.Platform%3DAndroid&hl=en-GB).

## Desktop

In a compatible Chromium browser, use the install icon in the address bar or
the browser menu. Firefox and some other browsers may not expose a native
install prompt; continue using the HTTPS site if no install option appears.

## Security reminders

- Install only from `https://delegateops.business/pimascor/`.
- The PWA does not bypass login, role checks, email verification, or session
  expiry.
- Do not install a similarly named app from an unverified link.
- Sign out on shared devices and report an unexpected install prompt to the
  PIMASCOR Administrator.

The web app manifest uses standalone display mode, stable relative identity,
PIMASCOR icons, and an `en-PH` locale. Chromium browsers receive a custom
`beforeinstallprompt` action when available; iOS receives the manual Safari
instructions because Apple does not expose that event there.
