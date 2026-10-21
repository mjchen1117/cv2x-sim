# 部署小抄：把 cv2x-sim 推上 GitHub

> 照抄即可。命令在 PowerShell 里按顺序执行，一行一条回车。

---

## 一次性准备

确认电脑上装了 `git`，在 PowerShell 输入 `git --version` 回车，出现版本号就说明装好了。

（如果报"不是内部或外部命令"：去 https://git-scm.com/download/win 安装 Git for Windows。）

---

## 第 1 步：在 GitHub 网页新建空仓库

1. 登录 github.com
2. 右上角 **+ → New repository**
3. Repository name 填：`cv2x-sim`
4. **不要勾选** "Add a README file"（空仓库）
5. 点绿色 **Create repository**

创建后页面会显示一串命令，**复制那页最下面的 SSH/HTTPS 地址**（形如 `https://github.com/你的名字/cv2x-sim.git`），下一步要用。

---

## 第 2 步：本地进到项目目录

在 PowerShell 里输入：

```bash
cd "d:\learning file\1\ex1\cv2x-sim"
```

---

## 第 3 步：初始化并推上去

依次逐行执行（每行回车后等它结束再敲下一行）：

```bash
git init
git add .
git commit -m "C-V2X 资源分配仿真：4 种调度算法对比"
git branch -M main
git remote add origin https://github.com/你的名字/cv2x-sim.git
git push -u origin main
```

- 第 5 行里的地址，换成你在第 1 步复制的那串。
- 第 6 行执行时若弹出"登录/GitHub"窗口，按提示登录授权即可。

---

## 完成后

- 打开 `github.com/你的名字/cv2x-sim`，应该能看到 README 和源码。
- `results/` 里的 `step7_scheduling.gif` 会自动显示成可播放的动画。

---

## 以后改代码再更新

每次改了代码想同步到 GitHub，重跑这三行：

```bash
git add .
git commit -m "更新说明"
git push
```

---

## 常见报错

| 报错 | 意思 | 解决 |
|------|------|------|
| `git is not recognized` | 没装 git | 重看"一次性准备" |
| `remote origin already exists` | 已绑定过仓库 | 把第 5 行 `git remote add` 改成 `git remote set-url origin 你的地址` |
| `fatal: Not a git repository` | 没先 git init | 回到第 3 步从 `git init` 开始 |
| push 时提示身份 | 首次要授权 | 按窗口提示登录，或用 `git config --global user.name "名字"` 和 `--global user.email "邮箱"` 先设置 |