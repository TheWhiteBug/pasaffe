# About

This is a fork of the excellent pasaffe project from https://launchpad.net/pasaffe

Refer to this site for latest updates in case this here gets out-of-date.

# Why

I use pasaffe on all my linux systems but I use the single PasswordSafe V3 DB on all my devices. It is automatically synced across all my devices using a distinct synching solution.

My DB is large and I need to search often.

* I was annoyed by the limited results returned by the "find" button.

# What

Since I was not interested in bzr, I cloned to bzr repo, converted it to git, created a "feature/improve-search" branch and pushed it here on github.

The "find" now works to my liking but is unlikely to be clean enough to be submitted as is upstream as a PR.

It now properly finds any record that matches the pattern in the title, username, url, password, notes, folder, etc.

# How

Clone the project, checkout the "feature/improve-search" branch, run pasaffe from the ./bin/ folder and enjoy.
