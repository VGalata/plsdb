Changes w.r.t. commit `6568949003525ebd6e02abb2de2b68348244d075`

- Conda requirements
    - Newer version:
        - umap-learn==0.3.7
        - mlst==2.15.2
        - abricate==0.8.10
        - snakemake==5.3.0
        - requests==2.20.1
    - Added to the list:
        - perl-net-ssleay==1.84
        - perl-libwww-perl==6.15
        - perl-lwp-protocol-https==6.07
- ABRicate:
    - "Patch" for updating VFDB is no longer required (issue was fixed in current release)
    - "Patch" for updating PlasmidFinder (`patch_abricate-get_db`, function `get_plasmidfinder`)
    - ARGannot is not updated because the URL is not working (error 404)
        - Using version from 20.10.2018 included in current ABRicate release
- Plasmid query: Retrieving accession + version instead of accession only
    - Field `Caption` was replaced by `AccessionVersion` in the `esearch` query
- Location table was updated based on new queries
- Filtering out plasmids (step 2)
    - Additional filtering after records with identical sequence were removed
        - Grouping by accession ID (without version)
     - New rule: If same accession keep the one with higher version number
    - New rule: If no rule applies decide by accession (w/ version)
        - To break ties
- UMAP: Package update, set min. distance parameter (default value), set seed
- Script to compare the created plasmid table to an older version