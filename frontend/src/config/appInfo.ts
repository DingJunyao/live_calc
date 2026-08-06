export interface AppInfo {
  name: string
  shortName: string
  version: string
  description: string
  copyright: string
  repository: string
  homepage: string
  authorHomepage: string
}

export const appInfo: AppInfo = __APP_INFO__
