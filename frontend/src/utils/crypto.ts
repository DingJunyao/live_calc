// utils/crypto.ts
import SHA256 from 'crypto-js/sha256'

/**
 * 对密码进行 SHA256 加密
 * @param password 原始密码
 * @returns 加密后的密码哈希值
 */
export function hashPassword(password: string): string {
  return SHA256(password).toString()
}
