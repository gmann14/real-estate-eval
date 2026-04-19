import { existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import type { Browser, BrowserContext, Page } from "playwright";
import { chromium } from "playwright";
import { getInternetPassword } from "./keychain.js";

const SESSION_PATH = ".session/viewpoint.json";
const LOGIN_URL = "https://www.viewpoint.ca/login";
const KEYCHAIN_SERVICE = "viewpoint.ca";
const DEFAULT_ACCOUNT = "graham_mann14@hotmail.com";

export interface ViewpointSession {
  browser: Browser;
  context: BrowserContext;
  page: Page;
}

export interface OpenSessionOptions {
  account?: string;
  headless?: boolean;
  forceLogin?: boolean;
}

async function performLogin(page: Page, account: string): Promise<void> {
  const password = await getInternetPassword({
    service: KEYCHAIN_SERVICE,
    account,
  });

  await page.goto(LOGIN_URL, { waitUntil: "domcontentloaded" });

  // Viewpoint login modal uses inputs name="login-email" / "login-password".
  // The form has no labelled "Login" button — it submits on Enter.
  const emailSelector = 'input[name="login-email"]';
  const passwordSelector = 'input[name="login-password"]';

  await page.waitForSelector(emailSelector, { state: "visible", timeout: 20_000 });
  await page.fill(emailSelector, account);
  await page.fill(passwordSelector, password);

  await Promise.all([
    page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => {}),
    page.press(passwordSelector, "Enter"),
  ]);

  // Give the post-login redirect / cookie set a moment to settle.
  await page.waitForTimeout(1_500);

  // Heuristic: success means the visible login form is gone. The modal
  // is dismissed on successful auth — the password input becomes hidden
  // or detached.
  const stillVisible = await page
    .locator(passwordSelector)
    .first()
    .isVisible()
    .catch(() => false);
  if (stillVisible) {
    throw new Error(
      `Login appears to have failed for ${account} (login modal still visible at ${page.url()})`,
    );
  }
}

function ensureSessionDir(): void {
  const dir = dirname(SESSION_PATH);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

export async function openSession(opts: OpenSessionOptions = {}): Promise<ViewpointSession> {
  const account = opts.account ?? DEFAULT_ACCOUNT;
  const headless = opts.headless ?? true;
  ensureSessionDir();

  const browser = await chromium.launch({ headless });
  const haveSession = !opts.forceLogin && existsSync(SESSION_PATH);
  const context = await browser.newContext(
    haveSession ? { storageState: SESSION_PATH } : undefined,
  );
  const page = await context.newPage();

  if (!haveSession) {
    await performLogin(page, account);
    await context.storageState({ path: SESSION_PATH });
  }

  return { browser, context, page };
}

export async function closeSession(session: ViewpointSession): Promise<void> {
  await session.context.close();
  await session.browser.close();
}
