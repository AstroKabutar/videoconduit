aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Project,Values=videoconduit \
  --query 'ResourceTagMappingList[].{ResourceARN:ResourceARN, Tags:Tags}' \
  --output table
