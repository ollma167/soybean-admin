import type { Browser, BrowserContext, Page } from 'playwright'

function resolveEnvNumber(value: string | undefined, fallback: number): number {
	const parsed = Number.parseInt(value ?? '', 10)
	return Number.isFinite(parsed) ? parsed : fallback
}

function resolveEnvBoolean(value: string | undefined, fallback: boolean): boolean {
	if (value === undefined) {
		return fallback
	}
	const normalized = value.trim().toLowerCase()
	if (normalized === 'false' || normalized === '0') {
		return false
	}
	if (normalized === 'true' || normalized === '1') {
		return true
	}
	return fallback
}

const NAVIGATION_TIMEOUT = resolveEnvNumber(process.env.DOUYIN_NAVIGATION_TIMEOUT, 60000)
const NOTE_SCRIPT_TIMEOUT = resolveEnvNumber(process.env.DOUYIN_SCRIPT_TIMEOUT, 60000)
const WARMUP_DELAY_MS = resolveEnvNumber(process.env.DOUYIN_WARMUP_DELAY, 3000)
const CHROMIUM_LAUNCH_TIMEOUT = resolveEnvNumber(process.env.DOUYIN_LAUNCH_TIMEOUT, 30000)
const AUTO_WARMUP_ENABLED = resolveEnvBoolean(process.env.DOUYIN_AUTO_WARMUP, false)
const AUTO_WARMUP_DELAY_MS = resolveEnvNumber(process.env.DOUYIN_AUTO_WARMUP_DELAY, 0)
const BROWSER_ENABLED = resolveEnvBoolean(process.env.DOUYIN_BROWSER_ENABLED, true)
const MAX_CONCURRENT_PAGES = Math.max(1, resolveEnvNumber(process.env.DOUYIN_MAX_CONCURRENCY, 1))
const CONTEXT_MAX_IDLE_MS = Math.max(0, resolveEnvNumber(process.env.DOUYIN_CONTEXT_MAX_IDLE, 2 * 60 * 1000))
const CONTEXT_MAX_USES = Math.max(1, resolveEnvNumber(process.env.DOUYIN_CONTEXT_MAX_USES, 50))
const BLOCKED_RESOURCE_TYPES = new Set(['image', 'media', 'font', 'stylesheet'])
const BLOCKED_URL_PATTERNS = [
	/\.(mp4|m3u8|m4s|mov)(\?|$)/i,
	/\/aweme\/v\d+\/playback\//i,
	/\/byteimg\.com\//i
]

interface ParsedNoteMediaItem {
	type: 'image' | 'video'
	url: string
	cover?: string | null
	duration?: number | null
	width?: number | null
	height?: number | null
	bitrate?: number | null
}

interface ParsedNoteResult {
	awemeId: string | null
	desc: string | null
	createTime: number | null
	author: {
		nickname: string | null
		secUid: string | null
		signature: string | null
	}
	stats: {
		commentCount: number | null
		diggCount: number | null
		shareCount: number | null
		collectCount: number | null
	}
	mediaItems: ParsedNoteMediaItem[]
}

interface NoteVideoCandidate {
	url: string
	bitrate?: number | null
	width?: number | null
	height?: number | null
	duration?: number | null
}

export interface NoteJsonData {
	aweme?: {
		detail?: {
			awemeId?: string
			desc?: string
			createTime?: number
			authorInfo?: {
				nickname?: string
				secUid?: string
				signature?: string
			}
			stats?: {
				commentCount?: number
				diggCount?: number
				shareCount?: number
				collectCount?: number
			}
			images?: Array<{
				urlList?: string[]
				width?: number
				height?: number
				video?: {
					bitRateList?: Array<{
						playApi?: string
						playAddr?: Array<{ src?: string }>
						playAddrH265?: Array<{ src?: string }>
						bitRate?: number
						bitrate?: number
						width?: number
						height?: number
						duration?: number
					}>
					playApi?: string
					playAddr?: Array<{ src?: string }>
					playAddrH265?: Array<{ src?: string }>
					bitRate?: number
					bitrate?: number
					width?: number
					height?: number
					duration?: number
				}
			}>
		}
	}
}

interface VideoData {
	bitRateList?: Array<{
		playApi?: string
		playAddr?: Array<{ src?: string }>
		playAddrH265?: Array<{ src?: string }>
		bitRate?: number
		bitrate?: number
		width?: number
		height?: number
		duration?: number
	}>
	playApi?: string
	playAddr?: Array<{ src?: string }>
	playAddrH265?: Array<{ src?: string }>
	bitRate?: number
	bitrate?: number
	width?: number
	height?: number
	duration?: number
}

let cachedBrowser: Browser | null = null
let playwrightModulePromise: Promise<typeof import('playwright')> | null = null
let cachedContext: BrowserContext | null = null
let contextInitPromise: Promise<BrowserContext> | null = null
let warmupPromise: Promise<void> | null = null
let activePages = 0
let contextUseCount = 0
let lastBrowserUse = 0
let contextCloseTimer: NodeJS.Timeout | null = null
const pendingAcquireResolvers: Array<() => void> = []

function markBrowserUsed(): void {
	lastBrowserUse = Date.now()
	if (contextCloseTimer) {
		clearTimeout(contextCloseTimer)
		contextCloseTimer = null
	}
}

async function disposeContext(reason: string): Promise<void> {
	const context = cachedContext
	cachedContext = null
	const browser = cachedBrowser
	cachedBrowser = null
	contextUseCount = 0
	lastBrowserUse = 0
	if (contextCloseTimer) {
		clearTimeout(contextCloseTimer)
		contextCloseTimer = null
	}
	activePages = 0
	if (pendingAcquireResolvers.length > 0) {
		console.warn(`Releasing pending Douyin Playwright page requests due to context disposal (${reason})`)
		const pendingResolvers = pendingAcquireResolvers.splice(0)
		for (const resolver of pendingResolvers) {
			resolver()
		}
	}

	if (context) {
		try {
			await context.close()
		} catch (error) {
			console.warn(`Failed to close Douyin Playwright context (${reason})`, error)
		}
	}

	if (browser) {
		try {
			await browser.close()
		} catch (error) {
			console.warn(`Failed to close Douyin Playwright browser (${reason})`, error)
		}
	}
}

function scheduleContextCleanup(): void {
	if (activePages > 0) {
		return
	}

	if (contextUseCount >= CONTEXT_MAX_USES) {
		void disposeContext('max-uses')
		return
	}

	if (CONTEXT_MAX_IDLE_MS === 0) {
		return
	}

	if (contextCloseTimer) {
		clearTimeout(contextCloseTimer)
	}

	contextCloseTimer = setTimeout(() => {
		if (activePages === 0 && cachedContext && Date.now() - lastBrowserUse >= CONTEXT_MAX_IDLE_MS) {
			void disposeContext('idle-timeout')
		}
	}, CONTEXT_MAX_IDLE_MS)

	if (typeof contextCloseTimer === 'object' && typeof contextCloseTimer.unref === 'function') {
		contextCloseTimer.unref()
	}
}

async function acquirePageSlot(): Promise<void> {
	if (activePages < MAX_CONCURRENT_PAGES) {
		activePages += 1
		return
	}

	await new Promise<void>((resolve) => {
		pendingAcquireResolvers.push(() => {
			activePages += 1
			resolve()
		})
	})
}

function releasePageSlot(): void {
	activePages = Math.max(0, activePages - 1)
	const next = pendingAcquireResolvers.shift()
	if (next) {
		next()
	}
	if (activePages === 0) {
		scheduleContextCleanup()
	}
}

async function getPlaywrightModule() {
	if (!playwrightModulePromise) {
		playwrightModulePromise = import('playwright')
	}
	return playwrightModulePromise
}

async function getBrowser(): Promise<Browser> {
	if (!BROWSER_ENABLED) {
		throw new Error('Douyin Playwright browser usage is disabled')
	}

	if (cachedBrowser?.isConnected()) {
		return cachedBrowser
	}

	const { chromium } = await getPlaywrightModule()
	cachedBrowser = await chromium.launch({
		headless: true,
		timeout: CHROMIUM_LAUNCH_TIMEOUT,
		args: ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-software-rasterizer']
	})

	cachedBrowser.on('disconnected', () => {
		cachedBrowser = null
		cachedContext = null
		warmupPromise = null
		contextUseCount = 0
		lastBrowserUse = 0
		if (contextCloseTimer) {
			clearTimeout(contextCloseTimer)
			contextCloseTimer = null
		}
	})

	markBrowserUsed()
	return cachedBrowser
}

async function initializeContext(): Promise<BrowserContext> {
	const { devices } = await getPlaywrightModule()
	const browser = await getBrowser()

	const context = await browser.newContext({
		...devices['Desktop Chrome'],
		locale: 'zh-CN',
		userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
		viewport: { width: 1280, height: 720 },
		bypassCSP: true
	})

	context.setDefaultNavigationTimeout(NAVIGATION_TIMEOUT)
	context.setDefaultTimeout(NAVIGATION_TIMEOUT)

	await context.route('**/*', (route) => {
		const request = route.request()
		const resourceType = request.resourceType()
		if (BLOCKED_RESOURCE_TYPES.has(resourceType)) {
			return route.abort()
		}
		const url = request.url()
		if (BLOCKED_URL_PATTERNS.some((pattern) => pattern.test(url))) {
			return route.abort()
		}
		return route.continue()
	})

	await context.addInitScript(() => {
		// disguise headless environment
		Object.defineProperty(navigator, 'webdriver', {
			get: () => undefined
		})
		;(window as unknown as Record<string, unknown>).chrome = { runtime: {} }
		Object.defineProperty(navigator, 'languages', {
			get: () => ['zh-CN', 'zh']
		})
		Object.defineProperty(navigator, 'plugins', {
			get: () => [1, 2, 3]
		})
	})

	context.on('close', () => {
		if (cachedContext === context) {
			cachedContext = null
		}
		warmupPromise = null
		contextUseCount = 0
		lastBrowserUse = 0
	})

	contextUseCount = 0
	markBrowserUsed()
	return context
}

async function performWarmup(): Promise<void> {
	if (!BROWSER_ENABLED) {
		return
	}

	await withPage(async (page) => {
		await page.goto('https://www.douyin.com/', {
			waitUntil: 'domcontentloaded',
			timeout: NAVIGATION_TIMEOUT
		})
		if (WARMUP_DELAY_MS > 0) {
			await page.waitForTimeout(WARMUP_DELAY_MS)
		}
	})
}

async function withPage<T>(handler: (page: Page) => Promise<T>): Promise<T> {
	if (!BROWSER_ENABLED) {
		throw new Error('Douyin Playwright browser usage is disabled')
	}

	await acquirePageSlot()
	let page: Page | null = null
	try {
		const context = await getContext()
		contextUseCount += 1
		page = await context.newPage()
		return await handler(page)
	} finally {
		try {
			await page?.close()
		} catch (error) {
			console.warn('Failed to close Douyin Playwright page', error)
		}
		releasePageSlot()
	}
}

async function getContext(): Promise<BrowserContext> {
	if (!BROWSER_ENABLED) {
		throw new Error('Douyin Playwright browser usage is disabled')
	}

	if (cachedContext) {
		markBrowserUsed()
		return cachedContext
	}

	if (!contextInitPromise) {
		contextInitPromise = initializeContext()
			.then((context) => {
				cachedContext = context
				return context
			})
			.finally(() => {
				contextInitPromise = null
			})
	}

	const contextPromise = contextInitPromise
	if (!contextPromise) {
		throw new Error('浏览器上下文初始化失败')
	}

	const context = await contextPromise
	markBrowserUsed()
	return context
}

export async function warmupDouyinNoteContext(): Promise<void> {
	if (!BROWSER_ENABLED) {
		return
	}

	if (!warmupPromise) {
		warmupPromise = (async () => {
			try {
				await performWarmup()
			} finally {
				warmupPromise = null
			}
		})()
	}

	await warmupPromise
}

function scheduleAutoWarmup() {
	if (!BROWSER_ENABLED || !AUTO_WARMUP_ENABLED) {
		return
	}

	const startWarmup = () => {
		warmupDouyinNoteContext().catch((error) => {
			console.warn('Douyin note auto warmup failed', error)
		})
	}

	if (AUTO_WARMUP_DELAY_MS > 0) {
		const timer = setTimeout(startWarmup, AUTO_WARMUP_DELAY_MS)
		if (typeof timer === 'object' && typeof (timer as NodeJS.Timeout).unref === 'function') {
			;(timer as NodeJS.Timeout).unref()
		}
		return
	}

	startWarmup()
}

scheduleAutoWarmup()

async function waitForNoteScript(page: Page): Promise<string> {
	const scriptHandle = await page.waitForFunction(
		() => {
			const scripts = Array.from(document.querySelectorAll('script'))
			const target = scripts.find((script) => script.textContent?.includes('awemeId'))
			return target?.textContent ?? null
		},
		{ timeout: NOTE_SCRIPT_TIMEOUT }
	)

	const scriptText = (await scriptHandle.jsonValue().catch(() => null)) as string | null
	await scriptHandle.dispose().catch(() => {})

	if (!scriptText) {
		throw new Error('未能获取到笔记数据脚本')
	}

	return scriptText
}

function unescapeScriptText(scriptText: string): string {
	const placeholder = '#__BACKSLASH_U__#'
	let result = scriptText.replace(/\\u/g, placeholder)
	result = result.replace(/\\"/g, '"')
	result = result.replace(/\\\\/g, '\\')
	return result.replace(new RegExp(placeholder, 'g'), '\\u')
}

function extractJsonSegment(unescapedScript: string): string {
	const marker = 'null,{"awemeId"'
	const markerIndex = unescapedScript.indexOf(marker)

	if (markerIndex === -1) {
		throw new Error('未找到笔记 JSON 数据入口')
	}

	const jsonStart = markerIndex + 'null,'.length
	let depth = 0
	let inString = false
	let escapeNext = false

	for (let i = jsonStart; i < unescapedScript.length; i++) {
		const ch = unescapedScript[i]

		if (escapeNext) {
			escapeNext = false
			continue
		}

		if (ch === '\\') {
			escapeNext = true
			continue
		}

		if (ch === '"') {
			inString = !inString
			continue
		}

		if (!inString) {
			if (ch === '{') {
				depth += 1
			} else if (ch === '}') {
				depth -= 1
				if (depth === 0) {
					return unescapedScript.slice(jsonStart, i + 1)
				}
			}
		}
	}

	throw new Error('未能完整提取笔记 JSON 数据')
}

function sanitizeJsonString(rawJson: string): string {
	return rawJson.replace(/"\$undefined"/g, 'null').replace(/"\$empty"/g, '""')
}

function decodeNoteScript(scriptText: string): NoteJsonData {
	const unescaped = unescapeScriptText(scriptText)
	const jsonSegment = extractJsonSegment(unescaped)
	const normalized = sanitizeJsonString(jsonSegment)
	return JSON.parse(normalized)
}

function extractNoteScriptFromHtml(html: string): string | null {
	const scriptRegex = /<script[^>]*>([\s\S]*?)<\/script>/g
	let match: RegExpExecArray | null = scriptRegex.exec(html)

	while (match !== null) {
		const scriptContent = match[1]?.trim()
		if (scriptContent?.includes('awemeId')) {
			return scriptContent
		}
		match = scriptRegex.exec(html)
	}

	return null
}

function selectBestVideoCandidate(video: VideoData | null | undefined): NoteVideoCandidate | null {
	const candidates: NoteVideoCandidate[] = []

	if (Array.isArray(video?.bitRateList)) {
		for (const item of video.bitRateList) {
			let candidateUrl = item?.playApi ?? item?.playAddr?.[0]?.src ?? item?.playAddrH265?.[0]?.src
			if (candidateUrl) {
				candidateUrl = candidateUrl.replace('playwm', 'play')
				candidates.push({
					url: candidateUrl,
					bitrate: item?.bitRate ?? item?.bitrate ?? null,
					width: item?.width ?? null,
					height: item?.height ?? null,
					duration: item?.duration ?? null
				})
			}
		}
	}

	const fallbackUrl = video?.playApi ?? video?.playAddr?.[0]?.src ?? video?.playAddrH265?.[0]?.src
	if (fallbackUrl) {
		candidates.push({
			url: fallbackUrl.replace('playwm', 'play'),
			bitrate: video?.bitRate ?? video?.bitrate ?? null,
			width: video?.width ?? null,
			height: video?.height ?? null,
			duration: video?.duration ?? null
		})
	}

	if (candidates.length === 0) {
		return null
	}

	return candidates.sort((a, b) => (b.bitrate ?? 0) - (a.bitrate ?? 0))[0]
}

function pickBestImageUrl(urlList: string[] | undefined): string | null {
	if (!urlList || urlList.length === 0) {
		return null
	}

	const preferred = urlList.find((item) => item.endsWith('.jpeg') || item.includes('.jpeg?'))
	return preferred ?? urlList[0]
}

function buildMediaItems(aweme: NoteJsonData['aweme'] | undefined): ParsedNoteMediaItem[] {
	if (!Array.isArray(aweme?.detail?.images)) {
		return []
	}

	const items: ParsedNoteMediaItem[] = []

	for (const image of aweme.detail.images) {
		const videoCandidate = selectBestVideoCandidate(image?.video)

		if (videoCandidate) {
			items.push({
				type: 'video',
				url: videoCandidate.url,
				cover: pickBestImageUrl(image?.urlList),
				duration: videoCandidate.duration ?? image?.video?.duration ?? null,
				width: videoCandidate.width ?? image?.video?.width ?? image?.width ?? null,
				height: videoCandidate.height ?? image?.video?.height ?? image?.height ?? null,
				bitrate: videoCandidate.bitrate ?? null
			})
			continue
		}

		const imageUrl = pickBestImageUrl(image?.urlList)
		if (imageUrl) {
			items.push({
				type: 'image',
				url: imageUrl,
				cover: imageUrl,
				duration: null,
				width: image?.width ?? null,
				height: image?.height ?? null
			})
		}
	}

	return items
}

export function mapNoteResultFromJson(noteJson: NoteJsonData): ParsedNoteResult {
	const detail = noteJson?.aweme?.detail ?? {}
	const authorInfo = detail?.authorInfo ?? {}
	const stats = detail?.stats ?? {}

	return {
		awemeId: (detail?.awemeId as string | undefined) ?? null,
		desc: (detail?.desc as string | undefined) ?? null,
		createTime: (detail?.createTime as number | undefined) ?? null,
		author: {
			nickname: (authorInfo?.nickname as string | undefined) ?? null,
			secUid: (authorInfo?.secUid as string | undefined) ?? null,
			signature: (authorInfo?.signature as string | undefined) ?? null
		},
		stats: {
			commentCount: (stats?.commentCount as number | undefined) ?? null,
			diggCount: (stats?.diggCount as number | undefined) ?? null,
			shareCount: (stats?.shareCount as number | undefined) ?? null,
			collectCount: (stats?.collectCount as number | undefined) ?? null
		},
		mediaItems: buildMediaItems(noteJson?.aweme)
	}
}

export function parseNoteFromHtml(html: string): ParsedNoteResult | null {
	try {
		const scriptText = extractNoteScriptFromHtml(html)
		if (!scriptText) {
			return null
		}
		const noteJson = decodeNoteScript(scriptText)
		return mapNoteResultFromJson(noteJson)
	} catch (error) {
		console.warn('parseNoteFromHtml failed', error)
		return null
	}
}

async function fetchNoteFromPage(url: string): Promise<ParsedNoteResult> {
	return withPage(async (page) => {
		await page.goto(url, { waitUntil: 'domcontentloaded', timeout: NAVIGATION_TIMEOUT })

		const scriptText = await waitForNoteScript(page)
		const noteJson = decodeNoteScript(scriptText)
		return mapNoteResultFromJson(noteJson)
	})
}

export async function parseDouyinNote(url: string): Promise<ParsedNoteResult> {
	if (!BROWSER_ENABLED) {
		throw new Error('Douyin Playwright browser usage is disabled')
	}
	return fetchNoteFromPage(url)
}

export type { ParsedNoteMediaItem, ParsedNoteResult }
