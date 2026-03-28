/**
 * SDK 脚本加载器
 * 负责动态加载和缓存地图 SDK 脚本
 */

export class SDKLoader {
  private loadedScripts: Map<string, Promise<void>> = new Map()
  private loadTimeout: number = 15000 // 15秒超时

  /**
   * 加载高德地图 SDK
   * @param key 高德地图 API Key
   * @param version SDK 版本，默认 2.0
   */
  loadAMap(key: string, version: string = '2.0'): Promise<void> {
    if (this.loadedScripts.has('amap')) {
      return this.loadedScripts.get('amap')!
    }

    const promise = this.loadScript(
      'amap',
      `https://webapi.amap.com/maps?v=${version}&key=${key}`
    )

    this.loadedScripts.set('amap', promise)
    return promise
  }

  /**
   * 加载百度地图 SDK
   * @param key 百度地图 API Key
   * @param useGL 是否使用 GL 版本，默认 false（使用 Legacy 版本）
   */
  loadBMap(key: string, useGL: boolean = false): Promise<void> {
    const scriptKey = useGL ? 'baidu-gl' : 'baidu'

    if (this.loadedScripts.has(scriptKey)) {
      return this.loadedScripts.get(scriptKey)!
    }

    // 百度地图需要使用 callback 参数避免 document.write 问题
    const callbackName = useGL ? '__baiduGLMapCallback__' : '__baiduMapCallback__'

    let url: string
    if (useGL) {
      // GL 版本
      url = `https://api.map.baidu.com/api?type=webgl&v=1.0&ak=${key}&callback=${callbackName}`
    } else {
      // Legacy 版本
      url = `https://api.map.baidu.com/api?v=3.0&ak=${key}&callback=${callbackName}`
    }

    const promise = this.loadScriptWithCallback(scriptKey, url, callbackName)
    this.loadedScripts.set(scriptKey, promise)
    return promise
  }

  /**
   * 加载腾讯地图 SDK
   * @param key 腾讯地图 API Key
   * @param version SDK 版本，默认 1.exp
   */
  loadTencentMap(key: string, version: string = '1.exp'): Promise<void> {
    if (this.loadedScripts.has('tencent')) {
      return this.loadedScripts.get('tencent')!
    }

    const promise = this.loadScript(
      'tencent',
      `https://map.qq.com/api/gljs?v=${version}&key=${key}`
    )

    this.loadedScripts.set('tencent', promise)
    return promise
  }

  /**
   * 通用脚本加载方法
   * @param name 脚本名称（用于缓存）
   * @param url 脚本 URL
   */
  private loadScript(name: string, url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // 检查是否已经加载（通过全局变量）
      if (this.isScriptLoaded(name)) {
        resolve()
        return
      }

      const script = document.createElement('script')
      script.type = 'text/javascript'
      script.src = url
      script.async = true

      // 设置超时
      const timeoutId = setTimeout(() => {
        reject(new Error(`Failed to load ${name} SDK: timeout`))
      }, this.loadTimeout)

      script.onload = () => {
        clearTimeout(timeoutId)
        console.log(`[SDKLoader] ${name} SDK loaded successfully`)
        resolve()
      }

      script.onerror = () => {
        clearTimeout(timeoutId)
        reject(new Error(`Failed to load ${name} SDK: load error`))
      }

      document.head.appendChild(script)
    })
  }

  /**
   * 使用回调函数方式加载脚本（用于百度地图等需要 JSONP 的 SDK）
   * @param name 脚本名称（用于缓存）
   * @param url 脚本 URL（包含 callback 参数）
   * @param callbackName 回调函数名称
   */
  private loadScriptWithCallback(name: string, url: string, callbackName: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // 检查是否已经加载（通过全局变量）
      if (this.isScriptLoaded(name)) {
        resolve()
        return
      }

      // 创建全局回调函数
      ;(window as any)[callbackName] = () => {
        console.log(`[SDKLoader] ${name} SDK loaded successfully via callback`)
        resolve()
      }

      const script = document.createElement('script')
      script.type = 'text/javascript'
      script.src = url
      script.async = true

      // 设置超时
      const timeoutId = setTimeout(() => {
        delete (window as any)[callbackName]
        reject(new Error(`Failed to load ${name} SDK: timeout`))
      }, this.loadTimeout)

      script.onerror = () => {
        clearTimeout(timeoutId)
        delete (window as any)[callbackName]
        reject(new Error(`Failed to load ${name} SDK: load error`))
      }

      document.head.appendChild(script)
    })
  }

  /**
   * 检查脚本是否已经加载
   * @param name 脚本名称
   */
  private isScriptLoaded(name: string): boolean {
    switch (name) {
      case 'amap':
        return typeof (window as any).AMap !== 'undefined'
      case 'baidu':
        return typeof (window as any).BMap !== 'undefined'
      case 'baidu-gl':
        return typeof (window as any).BMapGL !== 'undefined'
      case 'tencent':
        return typeof (window as any).TMap !== 'undefined'
      default:
        return false
    }
  }

  /**
   * 检查 SDK 是否可用
   * @param name SDK 名称
   */
  isSDKAvailable(name: string): boolean {
    return this.isScriptLoaded(name)
  }

  /**
   * 清理加载缓存
   * @param name 脚本名称，不传则清理所有
   */
  clear(name?: string): void {
    if (name) {
      this.loadedScripts.delete(name)
    } else {
      this.loadedScripts.clear()
    }
  }
}

// 导出单例
export const sdkLoader = new SDKLoader()
