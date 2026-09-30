export const eventTypes = [
  {
    value: 'INCIDENT', label: 'Incident', heading: 'Report a Crime', tag: 'INCIDENT REPORT',
    intro: 'Caught your suspect in the act? Add it to the permanent record.',
    categoryLabel: 'CRIME CATEGORY', icon: '!',
    categories: [
      'Food Theft', 'Property Damage', 'Sibling Assault', '3AM Zoomies',
      'Unauthorized Entry', 'Plant Destruction', 'Public Disturbance',
      'Furniture Damage', 'Suspicious Activity', 'Other',
    ],
  },
  {
    value: 'GOOD_CONDUCT', label: 'Good Conduct', heading: 'Record Good Conduct', tag: 'GOOD CONDUCT / COMMENDATION',
    intro: 'Every suspect deserves credit when they do something good.',
    categoryLabel: 'GOOD DEED', icon: '★',
    categories: ['Good Behavior', 'Learned Something New', 'Calm During Grooming', 'Friendly Interaction', 'Other'],
  },
  {
    value: 'FUNNY_MOMENT', label: 'Funny Moment', heading: 'Log Funny Moment', tag: 'FUNNY MOMENT / UNUSUAL ACTIVITY',
    intro: 'Some moments are too ridiculous to leave out of the file.',
    categoryLabel: 'MOMENT TYPE', icon: '✦',
    categories: ['Weird Sleeping Position', 'Funny Reaction', 'Got Stuck Somewhere', 'Random Chaos', 'Other'],
  },
  {
    value: 'WELLNESS', label: 'Wellness', heading: 'Add Wellness Check', tag: 'WELLNESS CHECK',
    intro: 'Keep a simple record of care, grooming, and checkups.',
    categoryLabel: 'CHECK TYPE', icon: '+',
    categories: ['Weight Check', 'Teeth Brushing', 'Nail Trim', 'Bath', 'Grooming', 'Other'],
  },
]

export const eventTypeByValue = Object.fromEntries(eventTypes.map((type) => [type.value, type]))
