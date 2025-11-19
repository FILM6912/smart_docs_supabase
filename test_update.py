import requests

# เข้าสู่ระบบเพื่อรับ token
login_data = {
    "email": "filmmagic69@gmail.com",
    "password": "film"
}
headers = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}
response = requests.post("http://localhost:8000/auth/login", data=login_data, headers=headers)
token = response.json()["access_token"]

# ข้อมูลสำหรับอัปเดตเอกสาร
update_data = {
  "docData": {
    "title": "Test Updated",
    "content": "55555\n![รูปภาพ](blob:http://localhost:5173/fd735971-bd60-4232-b96a-37d9d5354a4c)\n\nasdasdasd\n![รูปภาพ](blob:http://localhost:5173/0463fecd-5c82-455e-8963-0c8bae3d3034)\n\n```js\nconsole.log(\"kuay\")\n```",
    "category": "test"
  },
  "imgRef": [
    {
      "refer": "![รูปภาพ](blob:http://localhost:5173/fd735971-bd60-4232-b96a-37d9d5354a4c)",
      "imgByte": "iVBORw0KGgoAAAANSUhEUgAAAqYAAAJ+CAYAAABhFsLdAAAAAXNSR0IB2cksfwAAAAlwSFlzAAAOxAAADsQBlSsOGwAEv2pJREFUeJzsvQmUJFd553sjMrP2vaqrqvfu6uraMnKrvbvV6u5acqu9F4lFSKhbu2ihBQECQVlCbAYZg8fH582M5/nYfj4exvYsxsaM7fHYnoc9xst79gxn5nnwvoENDAh1V2bEvffd/d6slhA2gmzg+0EqszIjIiMis7r+8S3/DyEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA+A7Hq/cOAAAAAAAAAMDXAwQrAAAAAAAA8G3mzHa83rsAAAAAAAAAADUsve0Dnace/UDy7Jvfd/st977roRP3vONts5ffuj1379NPzF599uL8w89NTt233Xfp0sdj9d5XAAAAAAAA4LuIkw9/cN/cG9/++MjSbZ/rHz95vWVghMabByhq6qde20F2zx63DFKP3fsdB2jjnuO0Y2iG9mWXdsY37/ul6SvvvJ0J1ZZ6HwcAAAAAAADwHcjcG58+fjB/10/smyl/oaVvhCaY8ETNeynqHo7QvqkIHbklQofPhmh0cQdNLF9D48svoOEz19Ch+etobypEnUcj1HqIeqitGk/00K5jc9eGS3f+xuwDz5yu97EBAAAAAAAA3wFM37t9sn+q8Lfx9n0k1s7EaPfRKjrAxOZ48Tqa3Kyg7PkQZbdCf4o/Xo9Qit2CtaqXXtlBmRWMcusUTW1idotQbjNsSK9d84+cehG1HtlJNPSEsZa9tC+b/3zm7nc8emYb6lYBAAAAAACAXZx5aLvtyNLrP93YdoD6TT3Y60+GsZGz1+OplSrKboYoVYpQshh5QRl7qRWKxktVlFwJ2XNVNFGostcrKFUOUXoF+6kyZfdMwK5VvEy5Gptar8RmLuzEchvX0aGTFdQ0uOM17SHtEwtfWrj7qSv1PnYAAAAAAADg28eNtk7b275+OPGGtz3RPnoSo6Y+igbSNJbKUz/NxGWmTFBmhYtMdiuxW1nchDDlP+fEMuq1IkUBe5zSP7MbXzfLtiEeF8WyXmadepPrxB9bpGjvGEUdh6KB+fXPTT763N6a/bt0CRqnAAAAAAAAvtuZmrovoR/vXXjNrze29lPUfhCjVB6jmU2CsqtMkJYIShWYqCwwsVnkwpP9zAVmnt1KVnzy58QyJSwep/hySoymubDlP7Mbe+ylS/L5LLsxcRrLrlJ0cK6KmveTxv3ZavLOt9z5DR4C+KcCAAAAAAB8t3Dy8gfb9+UKf9TQ0kFRfyZC05vEm1qjKChEIropRScXkkxcFqgQmFKcqgiouqWL1EsVqFiOCVMvtUJE5DRtBKmMtLLHHlteRGJTKvqaXaF+dj30x/Mhaj9EvJ4hOnz7o++r97kBAAAAAAAAvjXcEF2cf+z55t7h6RfizZ0UHTuJ0exFJiLz1GOC0+MpeSEolQDlPxuhqkRlyomWilR+Qd4yJWzWEUK1oFL4KpWfXiE6pa+376eWCcqy98tshKh3vOo376XHtx7+CbGjkM4HAAAAAAD47oV3wg+MzO40NnZgf3T5Oppex4in1FNKMGZ4yl0ITYwCkcLHSmhSFJTkcjxqmlLRUxFB5fWlRarT/p4bFeVNU0Lslq2gDYpY16D6k+WKWDdZIN7kehX1jVfjHfvp8OaDP1fvcwUAAAAAAAB8Czk0XfxiQ3Mf9kYWrwu7JyFGed3nCpHiUYhQLAQnrwXN6hrTsltvqhqhSqrutCCFp26E4jWmUoQSt2lKNlGVZVNURgpTj7+PaKJiAjbFBPLUGkYDyZ1Y2wE6/JrHt9VuQ00pAAAAAADAdxMTK3d/OtbYTdGR0xGaXIv8VCkUXfOyXpQoASqFp4iIFohpfNLNTzy6GehUft"
    }
  ]
}

# ส่งคำขออัปเดตเอกสาร
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.put("http://localhost:8000/documents/22", json=update_data, headers=headers)
print("Status Code:", response.status_code)
print("Response:", response.json())