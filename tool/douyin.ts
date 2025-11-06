import { cache } from '$lib/cache'
import { randomBytes } from 'node:crypto'
import type { ParsedNoteMediaItem, ParsedNoteResult } from './douyin-note'
import { parseDouyinNote, parseNoteFromHtml } from './douyin-note'

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

const DOUYIN_CACHE_ENABLED = resolveEnvBoolean(process.env.DOUYIN_CACHE_ENABLED, true)
const DOUYIN_CACHE_TTL = resolveEnvNumber(process.env.DOUYIN_CACHE_TTL, 600)
const DOUYIN_NOTE_API_ENABLED = resolveEnvBoolean(process.env.DOUYIN_NOTE_API_ENABLED, true)

const CACHE_TYPE = 'douyin_info'
const API_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

function buildCacheKey(url: string): string | null {
	const trimmed = url.trim()
	if (!trimmed) {
		return null
	}
	return encodeURIComponent(trimmed)
}

async function readCachedInfo(candidates: Iterable<string>): Promise<DouyinEnhancedVideoInfo | null> {
	if (!DOUYIN_CACHE_ENABLED || DOUYIN_CACHE_TTL <= 0) {
		return null
	}
	for (const candidate of candidates) {
		const key = buildCacheKey(candidate)
		if (!key) {
			continue
		}
		const cached = await cache.get<DouyinEnhancedVideoInfo>(CACHE_TYPE, key)
		if (cached) {
			return cached
		}
	}
	return null
}

async function writeCachedInfo(candidates: Iterable<string>, value: DouyinEnhancedVideoInfo): Promise<void> {
	if (!DOUYIN_CACHE_ENABLED || DOUYIN_CACHE_TTL <= 0) {
		return
	}
	const uniqueKeys = new Set<string>()
	for (const candidate of candidates) {
		const key = buildCacheKey(candidate)
		if (key) {
			uniqueKeys.add(key)
		}
	}
	if (uniqueKeys.size === 0) {
		return
	}
	await Promise.all(Array.from(uniqueKeys).map((key) => cache.set(CACHE_TYPE, key, value, DOUYIN_CACHE_TTL)))
}

function pickFirstNonEmpty<T>(...values: Array<T | null | undefined>): T | undefined {
	for (const value of values) {
		if (value === undefined || value === null) {
			continue
		}
		if (typeof value === 'string' && value.trim() === '') {
			continue
		}
		return value
	}
	return undefined
}

function toNullableString(value: unknown): string | null {
	if (value === undefined || value === null) {
		return null
	}
	if (typeof value === 'string') {
		return value
	}
	if (typeof value === 'number' || typeof value === 'bigint') {
		return String(value)
	}
	return null
}

function toNullableNumber(value: unknown): number | null {
	if (value === undefined || value === null) {
		return null
	}
	if (typeof value === 'number') {
		return Number.isFinite(value) ? value : null
	}
	if (typeof value === 'string') {
		const trimmed = value.trim()
		if (!trimmed) {
			return null
		}
		const parsed = Number.parseFloat(trimmed)
		return Number.isFinite(parsed) ? parsed : null
	}
	return null
}

function toNullableInteger(value: unknown): number | null {
	const num = toNullableNumber(value)
	if (num === null) {
		return null
	}
	return Number.isFinite(num) ? Math.trunc(num) : null
}

function toNullableTimestampSeconds(value: unknown): number | null {
	const num = toNullableNumber(value)
	if (num === null) {
		return null
	}
	if (num > 1000000000000) {
		return Math.trunc(num / 1000)
	}
	return Math.trunc(num)
}

function pickFirstObject(...values: Array<unknown>): Record<string, unknown> | null {
	for (const value of values) {
		if (value && typeof value === 'object') {
			return value as Record<string, unknown>
		}
	}
	return null
}

function normalizeMediaUrl(url: string): string {
	return url.replace(/\\u002F/g, '/').replace(/playwm/g, 'play')
}

function extractUrlFromValue(value: unknown): string | null {
	if (value === undefined || value === null) {
		return null
	}
	if (typeof value === 'string') {
		const trimmed = value.trim()
		return trimmed ? normalizeMediaUrl(trimmed) : null
	}
	if (Array.isArray(value)) {
		for (const entry of value) {
			const extracted = extractUrlFromValue(entry)
			if (extracted) {
				return extracted
			}
		}
		return null
	}
	if (typeof value === 'object') {
		const candidate = pickFirstNonEmpty(
			(value as Record<string, unknown>).src,
			(value as Record<string, unknown>).url,
			(value as Record<string, unknown>).play_api,
			(value as Record<string, unknown>).playApi,
			(value as Record<string, unknown>).play_url,
			(value as Record<string, unknown>).main_url,
			(value as Record<string, unknown>).fallback_url,
			(value as Record<string, unknown>).download_url,
			(value as Record<string, unknown>).uri
		)
		const extracted = extractUrlFromValue(candidate)
		if (extracted) {
			return extracted
		}
		if ('url_list' in (value as Record<string, unknown>)) {
			const nested = extractUrlFromValue((value as Record<string, unknown>).url_list)
			if (nested) {
				return nested
			}
		}
		if ('play_addr' in (value as Record<string, unknown>)) {
			const nested = extractUrlFromValue((value as Record<string, unknown>).play_addr)
			if (nested) {
				return nested
			}
		}
		if ('playAddr' in (value as Record<string, unknown>)) {
			const nested = extractUrlFromValue((value as Record<string, unknown>).playAddr)
			if (nested) {
				return nested
			}
		}
		if ('download_addr' in (value as Record<string, unknown>)) {
			const nested = extractUrlFromValue((value as Record<string, unknown>).download_addr)
			if (nested) {
				return nested
			}
		}
	}
	return null
}

function collectImageEntries(detail: Record<string, unknown>): Record<string, unknown>[] {
	const candidates = [
		detail.images,
		detail.image_list,
		detail.image,
		detail.note_images,
		detail.imageInfos,
		detail.image_info,
		detail.image_data,
		detail.slides,
		detail.photo,
		detail.photo_list
	]
	const entries: Record<string, unknown>[] = []
	for (const candidate of candidates) {
		if (!candidate) {
			continue
		}
		if (Array.isArray(candidate)) {
			for (const item of candidate) {
				if (item && typeof item === 'object') {
					entries.push(item as Record<string, unknown>)
				}
			}
		} else if (typeof candidate === 'object') {
			entries.push(candidate as Record<string, unknown>)
		}
	}
	return entries
}

interface VideoCandidate {
	url: string
	bitrate?: number | null
	width?: number | null
	height?: number | null
	duration?: number | null
	cover?: string | null
}

function buildVideoCandidateFromSource(source: unknown): VideoCandidate | null {
	if (!source || typeof source !== 'object') {
		return null
	}
	const record = source as Record<string, unknown>
	const nestedCandidates = [
		record.bitRateList,
		record.bit_rate_list,
		record.play_info_list
	]
	let best: VideoCandidate | null = null

	const evaluate = (input: Record<string, unknown>): VideoCandidate | null => {
		const url = extractUrlFromValue(
			pickFirstNonEmpty(
				input.playApi,
				input.play_api,
				input.play_url,
				input.playAddr,
				input.play_addr,
				input.play_addr_h265,
				input.play_addr_h264,
				input.url,
				input.url_list,
				input.download_addr,
				input.src,
				input.uri
			)
		)
		if (!url) {
			return null
		}
		const bitrate = toNullableNumber(pickFirstNonEmpty(input.bitRate, input.bit_rate, input.bitrate))
		const width = toNullableNumber(pickFirstNonEmpty(input.width, input.video_width))
		const height = toNullableNumber(pickFirstNonEmpty(input.height, input.video_height))
		const duration = toNullableNumber(
			pickFirstNonEmpty(input.duration, input.video_duration, input.duration_ms ? Number(input.duration_ms) / 1000 : undefined)
		)
		const cover = extractUrlFromValue(pickFirstNonEmpty(input.cover, input.cover_url, input.poster, input.origin_cover))
		return {
			url,
			bitrate: bitrate ?? null,
			width: width ?? null,
			height: height ?? null,
			duration: duration ?? null,
			cover: cover ?? null
		}
	}

	const directCandidate = evaluate(record)
	if (directCandidate) {
		best = directCandidate
	}

	for (const nested of nestedCandidates) {
		if (!nested) {
			continue
		}
		const list = Array.isArray(nested) ? nested : [nested]
		for (const entry of list) {
			if (!entry || typeof entry !== 'object') {
				continue
			}
			const candidate = evaluate(entry as Record<string, unknown>)
			if (!candidate) {
				continue
			}
			if (!best || (candidate.bitrate ?? 0) > (best.bitrate ?? 0)) {
				best = candidate
			}
		}
	}

	return best
}

function buildMediaItemsFromApi(detail: Record<string, unknown>): ParsedNoteMediaItem[] {
	const items: ParsedNoteMediaItem[] = []
	const imageEntries = collectImageEntries(detail)

	for (const image of imageEntries) {
		const videoCandidate = buildVideoCandidateFromSource(
			pickFirstNonEmpty(image.video, image.video_info, image.videoData, image.video_data)
		)
		if (videoCandidate) {
			items.push({
				type: 'video',
				url: videoCandidate.url,
				cover: videoCandidate.cover ?? extractUrlFromValue(pickFirstNonEmpty(image.cover, image.url_list, image.url)),
				duration: videoCandidate.duration ?? null,
				width: videoCandidate.width ?? null,
				height: videoCandidate.height ?? null,
				bitrate: videoCandidate.bitrate ?? null
			})
			continue
		}

		const imageUrl = extractUrlFromValue(pickFirstNonEmpty(image.urlList, image.url_list, image.urls, image.url, image.uri))
		if (imageUrl) {
			const width = toNullableNumber(pickFirstNonEmpty(image.width, image.w, image.image_width))
			const height = toNullableNumber(pickFirstNonEmpty(image.height, image.h, image.image_height))
			items.push({
				type: 'image',
				url: imageUrl,
				cover: imageUrl,
				duration: null,
				width: width ?? null,
				height: height ?? null
			})
		}
	}

	if (!items.some((item) => item.type === 'video')) {
		const mediaRecord = pickFirstObject(detail.media)
		let fallbackVideoCandidate: VideoCandidate | null = buildVideoCandidateFromSource(
			pickFirstNonEmpty(
				detail.video,
				detail.video_data,
				detail.note_video,
				detail.video_info,
				mediaRecord?.video
			)
		)
		if (!fallbackVideoCandidate && Array.isArray(detail.video_list)) {
			for (const entry of detail.video_list as unknown[]) {
				const candidate = buildVideoCandidateFromSource(entry)
				if (!candidate) {
					continue
				}
				if (!fallbackVideoCandidate || (candidate.bitrate ?? 0) > (fallbackVideoCandidate.bitrate ?? 0)) {
					fallbackVideoCandidate = candidate
				}
			}
		}
		if (fallbackVideoCandidate) {
			const coverCandidate = extractUrlFromValue(
				pickFirstNonEmpty(
					detail.cover,
					detail.cover_url,
					detail.cover_url_list
				)
			)
			items.unshift({
				type: 'video',
				url: fallbackVideoCandidate.url,
				cover: fallbackVideoCandidate.cover ?? coverCandidate ?? null,
				duration: fallbackVideoCandidate.duration ?? null,
				width: fallbackVideoCandidate.width ?? null,
				height: fallbackVideoCandidate.height ?? null,
				bitrate: fallbackVideoCandidate.bitrate ?? null
			})
		}
	}

	const seen = new Set<string>()
	const deduped: ParsedNoteMediaItem[] = []
	for (const item of items) {
		if (!item.url) {
			continue
		}
		const key = `${item.type}:${item.url}`
		if (seen.has(key)) {
			continue
		}
		seen.add(key)
		deduped.push(item)
	}

	return deduped
}

function convertApiNoteToParsed(data: unknown): ParsedNoteResult | null {
	if (!data || typeof data !== 'object') {
		return null
	}
	const record = data as Record<string, unknown>
	const dataRecord = pickFirstObject(record.data)
	const noteDetailRecord = dataRecord ? pickFirstObject(dataRecord.note_detail) : null
	const recordNoteDetail = pickFirstObject(record.note_detail)
	const awemeDetailRecord = pickFirstObject(record.aweme_detail)
	const awemeRecord = pickFirstObject(record.aweme)
	const detailRecord = pickFirstObject(record.detail)

	const detailCandidate =
		pickFirstObject(noteDetailRecord?.note) ??
		pickFirstObject(noteDetailRecord?.detail) ??
		noteDetailRecord ??
		pickFirstObject(recordNoteDetail?.note) ??
		pickFirstObject(recordNoteDetail?.detail) ??
		recordNoteDetail ??
		pickFirstObject(record.note) ??
		pickFirstObject(awemeDetailRecord?.detail) ??
		awemeDetailRecord ??
		awemeRecord ??
		detailRecord ??
		record
	if (!detailCandidate) {
		return null
	}

	const statsSource =
		pickFirstObject(detailCandidate.stats) ??
		pickFirstObject(detailCandidate.statistics) ??
		pickFirstObject(detailCandidate.statistic) ??
		pickFirstObject(detailCandidate.note_stat) ??
		pickFirstObject(detailCandidate.note_statistics) ??
		(noteDetailRecord ? pickFirstObject(noteDetailRecord.statistics) : null) ??
		{}

	const authorSource =
		pickFirstObject(detailCandidate.authorInfo) ??
		pickFirstObject(detailCandidate.author_info) ??
		pickFirstObject(detailCandidate.author) ??
		pickFirstObject(detailCandidate.note_author) ??
		(noteDetailRecord ? pickFirstObject(noteDetailRecord.author) : null) ??
		pickFirstObject(record.author) ??
		{}

	const awemeId = toNullableString(
		pickFirstNonEmpty(
			detailCandidate.awemeId,
			detailCandidate.aweme_id,
			detailCandidate.note_id,
			detailCandidate.id,
			detailCandidate.id_str
		)
	)

	const desc = toNullableString(
		pickFirstNonEmpty(
			detailCandidate.desc,
			detailCandidate.content,
			detailCandidate.note_content,
			detailCandidate.title
		)
	)

	const createTime = toNullableTimestampSeconds(
		pickFirstNonEmpty(
			detailCandidate.create_time,
			detailCandidate.createTime,
			detailCandidate.publish_time,
			detailCandidate.pub_time
		)
	)

	const mediaItems = buildMediaItemsFromApi(detailCandidate)

	return {
		awemeId,
		desc,
		createTime,
		author: {
			nickname: toNullableString(pickFirstNonEmpty(authorSource.nickname, authorSource.nick_name, authorSource.name)),
			secUid: toNullableString(pickFirstNonEmpty(authorSource.sec_uid, authorSource.secUid)),
			signature: toNullableString(pickFirstNonEmpty(authorSource.signature, authorSource.desc, authorSource.signature_desc))
		},
		stats: {
			commentCount: toNullableInteger(pickFirstNonEmpty(statsSource.comment_count, statsSource.commentCount, statsSource.comment, statsSource.comments)),
			diggCount: toNullableInteger(pickFirstNonEmpty(statsSource.digg_count, statsSource.diggCount, statsSource.digg, statsSource.likes)),
			shareCount: toNullableInteger(pickFirstNonEmpty(statsSource.share_count, statsSource.shareCount, statsSource.share, statsSource.shares)),
			collectCount: toNullableInteger(pickFirstNonEmpty(statsSource.collect_count, statsSource.collectCount, statsSource.collect, statsSource.collects))
		},
		mediaItems
	}
}

function createMsToken(): string {
	return randomBytes(32).toString('hex')
}

function extractNoteId(url: string): string | null {
	const noteMatch = url.match(/note\/([0-9a-zA-Z]+)/)
	if (noteMatch) {
		return noteMatch[1]
	}
	const slidesMatch = url.match(/share\/slides\/([0-9a-zA-Z]+)/)
	if (slidesMatch) {
		return slidesMatch[1]
	}
	const modalMatch = url.match(/[?&]modal_id=(\d+)/)
	if (modalMatch) {
		return modalMatch[1]
	}
	return null
}

async function fetchNoteDetailViaApi(noteId: string): Promise<ParsedNoteResult | null> {
	if (!DOUYIN_NOTE_API_ENABLED) {
		return null
	}
	const msToken = createMsToken()
	const params = new URLSearchParams({
		note_id: noteId,
		device_platform: 'webapp',
		aid: '6383'
	})
	const apiUrl = `https://www.douyin.com/aweme/v1/web/note/detail/?${params.toString()}`
	const headers = new Headers()
	headers.set('User-Agent', API_USER_AGENT)
	headers.set('Referer', `https://www.douyin.com/note/${noteId}`)
	headers.set('Accept', 'application/json, text/plain, */*')
	headers.set('Cookie', `msToken=${msToken};`)

	try {
		const response = await fetch(apiUrl, { method: 'GET', headers })
		if (!response.ok) {
			return null
		}
		const json = await response.json().catch(() => null)
		if (!json) {
			return null
		}
		return (
			convertApiNoteToParsed(json.data) ??
			convertApiNoteToParsed(json)
		)
	} catch (error) {
		console.warn('fetchNoteDetailViaApi failed', error)
		return null
	}
}

async function cacheAndReturn(result: DouyinEnhancedVideoInfo, cacheKeys: Iterable<string>): Promise<DouyinEnhancedVideoInfo> {
	await writeCachedInfo(cacheKeys, result)
	return result
}

interface DouyinNoteItem {
	type: 'image' | 'video'
	url: string
	cover?: string | null
	duration?: number | null
	width?: number | null
	height?: number | null
	bitrate?: number | null
}

interface DouyinEnhancedVideoInfo {
	aweme_id: string | null
	comment_count: number | null
	digg_count: number | null
	share_count: number | null
	collect_count: number | null
	nickname: string | null
	signature: string | null
	desc: string | null
	create_time: string | null
	type: string | null
	video_url: string | null
	image_url_list: string[] | null
	note_items?: DouyinNoteItem[] | null
}

// 正则表达式模式
const pattern = /"video":{"play_addr":{"uri":"([a-z0-9]+)"/
const playAddrRegex = /"play_addr":\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/
const statsRegex = /"statistics"\s*:\s*\{([\s\S]*?)\},/
const regex = /"nickname":\s*"([^"]+)",\s*"signature":\s*"([^"]+)"/
const ctRegex = /"create_time":\s*(\d+)/
const descRegex = /"desc":\s*"([^"]+)"/

function formatDate(date: Date): string {
	const year = date.getFullYear()
	const month = String(date.getMonth() + 1).padStart(2, '0')
	const day = String(date.getDate()).padStart(2, '0')
	const hours = String(date.getHours()).padStart(2, '0')
	const minutes = String(date.getMinutes()).padStart(2, '0')
	const seconds = String(date.getSeconds()).padStart(2, '0')

	return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

async function doGet(url: string): Promise<Response> {
	const headers = new Headers()
	headers.set('User-Agent', 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36')
	const resp = await fetch(url, { method: 'GET', headers })
	return resp
}

// 从 play_addr 中提取视频 URL（无水印版本）
function parseVideoUrl(body: string): string | null {
	try {
		const playAddrMatch = body.match(playAddrRegex)
		if (!playAddrMatch) {
			console.warn('未找到 play_addr 信息')
			return null
		}

		const playAddrContent = playAddrMatch[0]

		const urlMatch = playAddrContent.match(/"url_list":\s*\[\s*"([^"]+)"/)
		if (!urlMatch) {
			console.warn('未找到 url_list')
			return null
		}

		// 添加无水印处理：将 playwm 替换为 play
		const videoUrl = urlMatch[1].replace(/\\u002F/g, '/').replace('playwm', 'play')

		return videoUrl
	} catch (error) {
		console.error('解析 play_addr 失败：', error)
		return null
	}
}

async function parseImgList(body: string): Promise<string[]> {
	const content = body.replace(/\\u002F/g, '/').replace(/\//g, '/')
	const reg = /{"uri":"[^\s"]+","url_list":\["(https:\/\/p\d{1,2}-sign.douyinpic.com\/.*?)"/g
	const urlRet = /"uri":"([^\s"]+)","url_list":/g

	let imgMatch: RegExpExecArray | null
	const firstUrls: string[] = []
	imgMatch = reg.exec(content)
	while (imgMatch !== null) {
		firstUrls.push(imgMatch[1])
		imgMatch = reg.exec(content)
	}

	let urlMatch: RegExpExecArray | null
	const urlList: string[] = []
	urlMatch = urlRet.exec(content)
	while (urlMatch !== null) {
		urlList.push(urlMatch[1])
		urlMatch = urlRet.exec(content)
	}
	const urlSet = new Set(urlList)
	const rList = []

	for (const urlSetKey of urlSet) {
		const t = firstUrls.find((item) => {
			return item.includes(urlSetKey)
		})
		if (t) {
			rList.push(t)
		}
	}

	const filteredRList = rList.filter((url) => !url.includes('/obj/'))
	console.log('filteredRList.length:', filteredRList.length)
	return filteredRList
}

// 尝试从 shipin 页面解析数据（URL编码的JSON格式）
function parseFromShipinPage(body: string): DouyinEnhancedVideoInfo | null {
	try {
		// 查找 URL 编码的 JSON 脚本（以 %7B 开头，即 { 的编码）
		const scriptRegex = /<script[^>]*>([\s\S]*?)<\/script>/g
		let match: RegExpExecArray | null

		match = scriptRegex.exec(body)
		while (match !== null) {
			const scriptContent = match[1].trim()

			if (scriptContent.startsWith('%7B') && scriptContent.length > 50000) {
				const decoded = decodeURIComponent(scriptContent)
				const data = JSON.parse(decoded)

				const videoData = data['1']?.data
				if (videoData?.main_video_info_str) {
					const mainVideo = JSON.parse(videoData.main_video_info_str)

					const result: DouyinEnhancedVideoInfo = {
						aweme_id: mainVideo.aweme_id || null,
						comment_count: mainVideo.statistics?.comment_count || null,
						digg_count: mainVideo.statistics?.digg_count || null,
						share_count: mainVideo.statistics?.share_count || null,
						collect_count: mainVideo.statistics?.collect_count || null,
						nickname: mainVideo.author?.nickname || null,
						signature: mainVideo.author?.signature || null,
						desc: mainVideo.desc || null,
						create_time: mainVideo.create_time ? formatDate(new Date(mainVideo.create_time * 1000)) : null,
						type: mainVideo.images && mainVideo.images.length > 0 ? 'img' : 'video',
						video_url: null,
						image_url_list: null
					}

					// 提取视频 URL
					if (mainVideo.video?.play_addr?.url_list && mainVideo.video.play_addr.url_list.length > 0) {
						const url = mainVideo.video.play_addr.url_list[0]
						result.video_url = url.replace('playwm', 'play')
					}

					// 提取图片列表
					if (mainVideo.images && mainVideo.images.length > 0) {
						result.image_url_list = mainVideo.images.map((img: { url_list?: string[] }) => img.url_list?.[0]).filter((url: string | undefined) => url && !url.includes('/obj/'))
					}

					return result
				}
			}

			match = scriptRegex.exec(body)
		}
	} catch (error) {
		console.warn('Failed to parse shipin page:', error)
	}

	return null
}

// 规范化 URL：提取视频 ID 并转换为标准格式
function normalizeDouyinUrl(url: string): string {
	// 1. 如果 URL 包含 modal_id 参数，提取它
	const modalIdMatch = url.match(/[?&]modal_id=(\d+)/)
	if (modalIdMatch) {
		const modalId = modalIdMatch[1]
		return `https://www.douyin.com/jingxuan?modal_id=${modalId}`
	}

	// 2. 如果是 /video/xxx 格式，提取视频 ID
	const videoIdMatch = url.match(/\/video\/(\d+)/)
	if (videoIdMatch) {
		const videoId = videoIdMatch[1]
		return `https://www.douyin.com/jingxuan?modal_id=${videoId}`
	}

	return url
}

function isNoteUrl(url: string): boolean {
	return url.includes('/note/') || url.includes('/share/slides/')
}

function mapNoteItems(mediaItems: ParsedNoteMediaItem[]): DouyinNoteItem[] {
	return mediaItems.map((item) => ({
		type: item.type,
		url: item.url,
		cover: item.cover ?? null,
		duration: item.duration ?? null,
		width: item.width ?? null,
		height: item.height ?? null,
		bitrate: item.bitrate ?? null
	}))
}

function transformNoteResult(parsed: ParsedNoteResult): DouyinEnhancedVideoInfo {
	const mediaItems = mapNoteItems(parsed.mediaItems)
	const imageUrls = mediaItems.filter((item) => item.type === 'image' && item.url).map((item) => item.url)

	const formattedTime = parsed.createTime && Number.isFinite(parsed.createTime) ? formatDate(new Date(parsed.createTime * 1000)) : null

	return {
		aweme_id: parsed.awemeId,
		comment_count: parsed.stats.commentCount,
		digg_count: parsed.stats.diggCount,
		share_count: parsed.stats.shareCount,
		collect_count: parsed.stats.collectCount,
		nickname: parsed.author.nickname,
		signature: parsed.author.signature,
		desc: parsed.desc,
		create_time: formattedTime,
		type: 'note',
		video_url: null,
		image_url_list: imageUrls.length > 0 ? imageUrls : null,
		note_items: mediaItems
	}
}

async function getEnhancedVideoInfo(url: string): Promise<DouyinEnhancedVideoInfo> {
	// 规范化 URL
	const trimmedUrl = url.trim()
	const normalizedUrl = normalizeDouyinUrl(trimmedUrl)
	const cacheKeyCandidates = new Set<string>([trimmedUrl, normalizedUrl])

	const cached = await readCachedInfo(cacheKeyCandidates)
	if (cached) {
		return cached
	}

	const resp = await doGet(normalizedUrl)
	const finalUrl = resp.url
	cacheKeyCandidates.add(finalUrl)
	const body = await resp.text()
	const shipinResult = parseFromShipinPage(body)
	if (shipinResult) {
		return cacheAndReturn(shipinResult, cacheKeyCandidates)
	}

	const targetUrl = isNoteUrl(finalUrl) ? finalUrl : normalizedUrl
	cacheKeyCandidates.add(targetUrl)

	if (isNoteUrl(targetUrl)) {
		const parsedFromHtml = parseNoteFromHtml(body)
		if (parsedFromHtml) {
			return cacheAndReturn(transformNoteResult(parsedFromHtml), cacheKeyCandidates)
		}
		const noteId = extractNoteId(targetUrl)
		if (noteId) {
			cacheKeyCandidates.add(`https://www.douyin.com/note/${noteId}`)
			const apiNote = await fetchNoteDetailViaApi(noteId)
			if (apiNote) {
				return cacheAndReturn(transformNoteResult(apiNote), cacheKeyCandidates)
			}
		}
		const parsedNote = await parseDouyinNote(targetUrl)
		return cacheAndReturn(transformNoteResult(parsedNote), cacheKeyCandidates)
	}

	// 回退到原始格式（jingxuan、modal 等）
	let type = 'video'
	let img_list: string[] = []
	let video_url: string | null = null

	const match = pattern.exec(body)

	if (!match || !match[1]) {
		type = 'img'
	}

	if (type === 'video') {
		video_url = parseVideoUrl(body)
	} else {
		img_list = await parseImgList(body)
	}

	const auMatch = body.match(regex)
	const ctMatch = body.match(ctRegex)
	const descMatch = body.match(descRegex)
	const statsMatch = body.match(statsRegex)

	if (statsMatch) {
		const innerContent = statsMatch[0]

		const awemeIdMatch = innerContent.match(/"aweme_id"\s*:\s*"([^"]+)"/)
		const commentCountMatch = innerContent.match(/"comment_count"\s*:\s*(\d+)/)
		const diggCountMatch = innerContent.match(/"digg_count"\s*:\s*(\d+)/)
		const shareCountMatch = innerContent.match(/"share_count"\s*:\s*(\d+)/)
		const collectCountMatch = innerContent.match(/"collect_count"\s*:\s*(\d+)/)

		const douyinVideoInfo: DouyinEnhancedVideoInfo = {
			aweme_id: awemeIdMatch ? awemeIdMatch[1] : null,
			comment_count: commentCountMatch ? Number.parseInt(commentCountMatch[1], 10) : null,
			digg_count: diggCountMatch ? Number.parseInt(diggCountMatch[1], 10) : null,
			share_count: shareCountMatch ? Number.parseInt(shareCountMatch[1], 10) : null,
			collect_count: collectCountMatch ? Number.parseInt(collectCountMatch[1], 10) : null,
			nickname: null,
			signature: null,
			desc: null,
			create_time: null,
			type: type,
			video_url: video_url,
			image_url_list: img_list
		}

		if (auMatch) {
			douyinVideoInfo.nickname = auMatch[1]
			douyinVideoInfo.signature = auMatch[2]
		}

		if (ctMatch) {
			const date = new Date(Number.parseInt(ctMatch[1], 10) * 1000)
			douyinVideoInfo.create_time = formatDate(date)
		}

		if (descMatch) {
			douyinVideoInfo.desc = descMatch[1]
		}

		return cacheAndReturn(douyinVideoInfo, cacheKeyCandidates)
	}
	throw new Error('No stats found in the response.')
}

export { getEnhancedVideoInfo }
export type { DouyinEnhancedVideoInfo, DouyinNoteItem }
