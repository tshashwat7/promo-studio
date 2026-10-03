# Connect Instagram (and optionally Facebook) to Social Promo Studio

Menu names in Meta's dashboard change from time to time. If a label differs, follow Meta's current docs:
developers.facebook.com/documentation/instagram-platform (Get Started / Create a Meta App).

## A. Instagram (no Facebook Page needed)

Requirements: a **Business or Creator** Instagram account, set to **public** while you add it.

1. Sign in at developers.facebook.com and open **My Apps > Create App**.
2. Use case: **Other**. App type: **Business**. Enter an app name and contact email, then create the app.
3. On the app dashboard find the **Instagram** product and click **Set up**.
   Use **API setup with Instagram login** (not "with Facebook login").
4. Open **Instagram > API setup with Instagram login**. Under **Generate access tokens** click **Add account**,
   sign in to @siddhanta.app and accept the permissions.
5. Click **Generate token** next to the account and copy it. Tokens generated in the dashboard are long-lived
   (about 60 days).
6. Find the account's **Instagram user ID**. The dashboard shows it, or call
   `https://graph.instagram.com/v25.0/me?fields=user_id,username` with the token
   (header `Authorization: Bearer <token>`); use the `user_id` value.
7. In Social Promo Studio open **Settings > Publishing accounts** and paste:
   - Instagram user ID
   - Instagram access token
   - Image host API key (see B)
   then **Save settings**, **Test Instagram**, and finally **Refresh Instagram token** so the app records the new
   expiry date and warns you a week before it runs out.

If Meta asks for business verification or app review before the token works, tell me exactly what it asks: for
your own account the development-mode app should be enough, but I have not been able to confirm this against your
account.

## B. Image host (required for Instagram)

Instagram downloads the image from a public URL when you publish, so the app uploads a temporary copy first.

1. Create a free account at imgbb.com and get an API key (api.imgbb.com).
2. Paste it in **Settings > Image host API key**. Uploads auto-expire after one hour.
3. The first real Instagram post is the real test that Instagram can fetch images from this host. If it fails with
   "could not process the image", tell me and I will add a second host (for example Cloudinary).

## C. Facebook Page (only when you want Facebook posting)

Facebook posting needs a **Page** (personal profiles are not supported by the API).

1. Create a Page for Siddhanta (or use an existing one).
2. In the same Meta app add the Facebook/Pages permissions, generate a **Page access token** for that Page and note
   the **Page ID**. Steps differ by app mode, so use Meta's Pages API docs alongside this guide.
3. Paste Page ID and Page token in **Settings > Publishing accounts**, then **Test Facebook**.

Until then, leave the Facebook fields empty: the app simply reports "Not configured" for Facebook and posts to
Instagram.

## D. Good habits

- Start with one real post to Instagram using a test caption, and delete it afterwards.
- Instagram allows a limited number of API-published posts per 24 hours (100 in Meta's docs), far above what you need.
- Never paste tokens into chat, screenshots or Git. The app stores them in your OS keyring.
