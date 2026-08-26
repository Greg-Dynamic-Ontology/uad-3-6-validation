# OTDD Feature Numbering
## Basics
**Rules**
1. IT   :   Iteration
2. "-"  :   '-' separator  
3. nn   :   Iteration Number from 1 to 99
4. 'R'  :   Rule marker
5. n    :   Rule Number within the feature file from 1 to 9

**Scenarios**
6. 'S'  :   Scenario marker
7. n    :   Scenario Number within the rule from 1 to 9

## Details
- Each iteration spans the work selected from one feature file and may contain one or more rules.
- Iteration Number is cumulatively incremented across the project
- Rule Number is incremented for each rule in the file
- "IT-99R1" is the 99th iteration of the project, the first Rule in the feature file we are implementing
- "IT-99R1S1" is the first scenario in the first rule of the 99th iteration

## Expansion
- If more than 99 iterations are needed, the iteration number is incremented to 1NN
- "IT-100R1" is the 100th iteration of the project, the first Rule in the feature file we are implementing
- If more than 9 rules in one feature file N is incremented to 1N
- "IT-199R10S1" is the first scenario in the 10th rule of the 199th iteration
- If more than 9 scenarios in one rule N is incremented to 1N
- "IT-199R10S10" is the tenth scenario in the 10th rule of the 199th iteration
Note: If work is properly divided, these expansions are not needed.
Except a huge project may need more than 99 iterations.

## Break-ups
When a feature file needs to be broken up into smaller pieces, the OTDD Feature Numbering will
take on an alphabetic suffix.

@IT-22R1-A
@IT-22R1-B