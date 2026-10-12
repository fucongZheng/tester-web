// 密码传输统一走 RSA 加密（登录、用户管理等），避免报文里出现明文密码。
// 后端公钥随进程重启更换，前端拉取后模块级缓存；解密失败时后端会报错，调用方提示刷新重试即可。
import JSEncrypt from 'jsencrypt'
import request from '../api/request'

let cachedKey = ''

export async function fetchRsaKey(force = false) {
  if (!cachedKey || force) {
    cachedKey = (await request.get('/auth/rsa-key')).public_key || ''
  }
  return cachedKey
}

/** 加密失败返回空串（调用方应提示重试，并用 fetchRsaKey(true) 刷新公钥） */
export async function encryptPassword(pwd) {
  const key = await fetchRsaKey().catch(() => '')
  if (!key) return ''
  const encryptor = new JSEncrypt()
  encryptor.setPublicKey(key)
  return encryptor.encrypt(pwd) || ''
}
