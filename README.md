# EnergyMarket (Python)

## Executing with virtualenv
    $ git clone https://github.com/gforien/energymarket
    $ cd energymarket
    $ mkdir launch_dir
    $ virtualenv launch_dir
    $ source launch_dir/bin/activate
    (launch_dir) $ pip install matplotlib sysv_ipc

## Annexe - Rappel du cycle de vie d'un projet git
##### 1) Simple commit
```
$ git status
-> Sur la branche master
$ vim fichier1 fichier2                                 # modifications
$ git add fichier1 fichier2
$ git commit -m "Commit sur la branche principale"
$ git pull && git push
```
##### 2) Création d'une nouvelle branche, commits, et fermeture de la branche
```
$ git checkout -b gui
-> Sur la nouvelle branche gui

$ vim fichier1 fichier2                                 # modifications
$ git add fichier1 fichier2
$ git commit -m "Commit sur la branche gui"
$ git push -u                                           # -u si la branche n'existe pas déjà sur le serveur

$ vim fichier1 fichier2                                 #  nouvelles modifications
$ git add fichier1 fichier2
$ git commit -m "2e commit sur la branche gui"
$ git push                                              # cette fois la branche existe déjà sur le serveur

$ git checkout master
-> Sur la branche master
$ git merge --no-ff gui                                 # on rapatrie la branche master sur la branche gui
$ git branch -d gui                                     # supprime la branche gui
$ git pull && git push
```
##### 3) Sauvegarder le travail en cours pour travailler sur la branche principale
```
$ git st
-> Changes not staged for commit : fichier1
$ git stash                                             # enregistre fichier1 en mémoire et restaure le dernier commit

$ vim fichier1 fichier2                                 # modifications
$ git add fichier1 fichier2
$ git commit -m "Commit sur la branche principale"
$ git pull && git push

$ git stash pop                                           # restaure fichier1
```

##
###### Elisa BOUVET, Gabriel FORIEN<br/>3TC INSA Lyon
![Logo INSA Lyon](https://upload.wikimedia.org/wikipedia/commons/b/b9/Logo_INSA_Lyon_%282014%29.svg)
